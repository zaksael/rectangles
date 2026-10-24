"""Records the Python server's wire traffic for scripted games into the golden fixtures the Scala port is checked against.

Usage (from the repo root): uv run python -m scripts.regenerate_golden [--check]

Each scenario drives a real `/ws` session with a fixed policy and a recording random source, so a second run writes the same bytes.
`--check` regenerates in memory and fails if a file on disk differs. Deleted together with the Python server.
"""

import json
import random
import sys
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode

from starlette.testclient import TestClient

from rectangles.engine.constants import PLAYER_1
from rectangles.engine.game import Game
from rectangles.server import app as server_app

GOLDEN_DIR = Path(__file__).resolve().parents[1] / "server-scala" / "server" / "src" / "test" / "resources" / "golden"
PROTOCOL_VERSION = 1


class RecordingRandom(random.Random):
    """A seeded random source that logs every draw as `[kind, ...args, value]`, for the Scala port to replay in order."""

    def __init__(self, seed: int):
        super().__init__(seed)
        self.draws: list[list] = []

    def randint(self, a, b):
        value = super().randint(a, b)
        self.draws.append(["randint", a, b, value])
        return value

    def choice(self, seq):
        index = self._randbelow(len(seq))
        self.draws.append(["choice", len(seq), index])
        return seq[index]


@dataclass(frozen=True)
class Scenario:
    name: str
    query: dict
    seed: int
    moves: int = 12  # placements or skips the policy plays before it surrenders
    pinned: bool = True  # Player 1 opens (no coin-flip draw); False records the real flip, compared by keys only
    use_reroll: bool = False  # reroll the first roll of each of the first two turns
    tail: list = field(default_factory=list)  # raw client messages sent after the surrender: dicts are JSON, strings are sent as text
    probes: list = field(default_factory=list)  # raw client messages sent right after connecting, before any play
    must_see: tuple = ()  # strings that must appear in the recorded replies, so a scenario cannot silently stop covering its rule
    rounds: int = 1  # series: games played, continuing with `continueSeries` between them


def msg(type_: str, **fields) -> dict:
    return {"protocolVersion": PROTOCOL_VERSION, "type": type_, **fields}


RULES = {
    "walls": "wallsEnabled",
    "obstacles": "obstaclesEnabled",
    "prize": "prizeEnabled",
    "pitfall": "pitfallEnabled",
    "steal": "stealEnabled",
    "self-enclosed": "selfEnclosedPenaltyEnabled",
    "reroll": "rerollEnabled",
    "comeback": "comebackNudgeEnabled",
    "wildcard": "wildcardEnabled",
}
ALL_RULES = {flag: "true" for flag in RULES.values()}

SCENARIOS = [
    Scenario("vanilla", {"boardSize": 19}, seed=1),
    Scenario("game-over", {"boardSize": 19}, seed=2, moves=6, tail=[msg("requestAnalysis")], must_see=("analysis",)),
    Scenario(
        "errors",
        {"boardSize": 19},
        seed=3,
        moves=2,
        probes=[
            "not json",
            {"protocolVersion": PROTOCOL_VERSION},
            {"protocolVersion": 2, "type": "roll"},
            msg("place", topLeft=[0, 0], width=2, height=2),
            msg("skip"),
            msg("reroll"),
            msg("chooseWildcard", value=3),
            msg("place", topLeft="x", width=2, height=2),
            msg("explode"),
            msg("requestAnalysis"),
            msg("continueSeries"),
            msg("roll"),
            msg("roll"),
            msg("place", topLeft=[10, 10], width=1, height=1),
        ],
        must_see=("invalidAction", "illegalPlacement", "protocolVersionMismatch", "malformedMessage"),
    ),
    *[
        Scenario(name, {"boardSize": 19, flag: "true"}, seed=10 + i)
        for i, (name, flag) in enumerate(RULES.items())
        if name not in ("reroll", "wildcard", "self-enclosed", "comeback")
    ],
    # These two rules show up in the wire only once a game gets that far, so their seeds were picked for it (and must_see keeps them honest).
    Scenario("self-enclosed", {"boardSize": 19, "selfEnclosedPenaltyEnabled": "true"}, seed=19, moves=14, must_see=('"enclosure": -',)),
    Scenario("comeback", {"boardSize": 19, "comebackNudgeEnabled": "true"}, seed=17, must_see=('"granted": true',)),
    Scenario("reroll", {"boardSize": 19, "rerollEnabled": "true"}, seed=30, use_reroll=True, must_see=('"canReroll": true',)),
    Scenario("wildcard", {"boardSize": 19, "wildcardEnabled": "true"}, seed=31, moves=40, must_see=("choosingWildcard", "illegalWildcardValue")),
    Scenario("prize-walls-obstacles", {"boardSize": 19, "prizeEnabled": "true", "wallsEnabled": "true", "obstaclesEnabled": "true"}, seed=41, moves=8),
    Scenario("all-rules", {"boardSize": 19, **ALL_RULES}, seed=40, moves=16, use_reroll=True),
    Scenario("series", {"boardSize": 19, "seriesLength": 3}, seed=50, moves=3, rounds=3, must_see=('"series": {',)),
    Scenario("bot-random-starter", {"boardSize": 19, "botSeats": 2, "botDifficulty": "Greedy"}, seed=60, moves=8, pinned=False),
]


def query_string(scenario: Scenario) -> str:
    return urlencode({"protocolVersion": PROTOCOL_VERSION, **scenario.query})


def game_state(reply: dict) -> dict:
    return reply["game"]["turn"]


def my_turn(reply: dict) -> bool:
    """True once a state reply is one the human player must act on (or the game is over)."""
    game = reply["game"]
    return game["gameOver"]["reason"] is not None or game["turn"]["currentPlayerId"] == PLAYER_1


class Recorder:
    """Sends client messages over a socket and records each send with the replies it produced."""

    def __init__(self, scenario: Scenario, ws):
        self.scenario = scenario
        self.ws = ws
        self.steps: list[dict] = []
        self.last: dict = {}
        self.last_state: dict = {}  # the latest `state` reply, which the policy plays from even after an error reply

    def __call__(self, message) -> None:
        if isinstance(message, str):
            self.ws.send_text(message)
        else:
            self.ws.send_json(message)
        self.collect(message)

    def collect(self, message) -> None:
        """Reads the replies to `message` (None for the connect) and records them as one step."""
        replies = [self.ws.receive_json()]
        # A bot seat answers with extra state messages until it is the human's turn again.
        while "botSeats" in self.scenario.query and replies[-1]["type"] == "state" and not my_turn(replies[-1]):
            replies.append(self.ws.receive_json())
        self.steps.append({"send": message, "receive": replies})
        self.last = replies[-1]
        states = [reply for reply in replies if reply["type"] == "state"]
        if states:
            self.last_state = states[-1]


def run(scenario: Scenario) -> dict:
    rng = RecordingRandom(scenario.seed)
    with ExitStack() as stack:
        stack.enter_context(patch.object(server_app, "Game", partial(Game, rng=rng)))
        stack.enter_context(patch("rectangles.engine.series.Game", partial(Game, rng=rng)))
        if scenario.pinned:
            def pinned(query_params):
                game = Game(**server_app._rules_kwargs_from_connect_params(query_params), rng=rng)
                game.current_player_id = PLAYER_1
                return game

            stack.enter_context(patch.object(server_app, "_game_from_connect_params", pinned))
        client = TestClient(server_app.app)
        with client.websocket_connect(f"/ws?{query_string(scenario)}") as ws:
            recorder = Recorder(scenario, ws)
            recorder.collect(None)
            for probe in scenario.probes:
                recorder(probe)
            for round_number in range(scenario.rounds):
                play_round(scenario, recorder)
                if round_number < scenario.rounds - 1:
                    recorder(msg("continueSeries"))
            for message in scenario.tail:
                recorder(message)
    text = json.dumps(recorder.steps)
    for needle in scenario.must_see:
        if needle not in text:
            raise RuntimeError(f"{scenario.name}: the recording never shows {needle!r}")
    return {"name": scenario.name, "connect": {"protocolVersion": PROTOCOL_VERSION, **scenario.query}, "pinnedStarter": scenario.pinned,
            "draws": rng.draws, "steps": recorder.steps}


def play_round(scenario: Scenario, recorder: Recorder) -> None:
    moves = 0
    rerolled = 0
    last = recorder.last_state
    while moves < scenario.moves:
        turn = game_state(last)
        state = turn["turnState"]
        if state == "awaitingRoll":
            recorder(msg("roll"))
        elif state == "choosingWildcard":
            for value in (7, 1, 2, 3, 4, 5, 6):  # 7 is out of range: the recording keeps an illegalWildcardValue reply
                recorder(msg("chooseWildcard", value=value))
                if recorder.last["type"] == "state":
                    break
        elif state == "choosingPlacement":
            if scenario.use_reroll and rerolled < 2 and last["game"]["houseRules"]["reroll"]["canReroll"]:
                rerolled += 1
                recorder(msg("reroll"))
                last = recorder.last_state
                continue
            placement = turn["legalPlacements"][0]
            recorder(msg("place", topLeft=min(placement["topLefts"]), width=placement["width"], height=placement["height"]))
            moves += 1
        elif state == "skipped":
            recorder(msg("skip"))
            moves += 1
        else:
            raise RuntimeError(f"{scenario.name}: unexpected turn state {state}")
        last = recorder.last_state
    recorder(msg("surrender"))


def render(recording: dict) -> str:
    """One line per client step, so a changed fixture diffs line by line."""
    head = {key: value for key, value in recording.items() if key != "steps"}
    lines = [json.dumps(step, separators=(",", ":")) for step in recording["steps"]]
    return json.dumps(head, separators=(",", ":"))[:-1] + ',"steps":[\n' + ",\n".join(lines) + "\n]}\n"


def main() -> int:
    check = "--check" in sys.argv
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    stale = []
    for scenario in SCENARIOS:
        text = render(run(scenario))
        path = GOLDEN_DIR / f"{scenario.name}.json"
        if check:
            if not path.exists() or path.read_text() != text:
                stale.append(path.name)
        else:
            path.write_text(text)
            print(f"{path.name}: {len(text) // 1024} KB")
    if stale:
        print("stale golden files:", ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
