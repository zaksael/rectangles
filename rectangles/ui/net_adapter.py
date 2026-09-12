"""Drop-in proxy for `Game`, used by ui/input.py to talk to the M1 server
over the wire instead of calling a local Game object in-process. Method
signatures mirror Game's exactly so ui/input.py's call sites don't change,
only which object they call.

A background thread owns an asyncio event loop and the websocket
connection; every received `state` message repopulates this adapter's own
public attributes (mirroring Game's real fields) since ui/renderer.py reads
those attributes directly, not through methods.

Action methods (roll_dice/attempt_place/confirm_skip/surrender) are still
stubs - wiring them through `_request` with error-reason mapping is a
separate task."""

from __future__ import annotations

import asyncio
import json
import queue
import threading

import websockets

from rectangles.board import Board
from rectangles.constants import CellKind
from rectangles.game import GameOverReason
from rectangles.models import Player
from server import schema

_TURN_STATE_FROM_WIRE = {v: k for k, v in schema._TURN_STATE_NAMES.items()}
_GAME_OVER_REASON_FROM_WIRE = {v: k for k, v in schema._GAME_OVER_REASON_NAMES.items()}

_REQUEST_TIMEOUT = 10.0


def _player_from_wire(player_id: int, board: Board, data: dict) -> Player:
    player = Player(
        id=player_id,
        name=data["name"],
        start_corner=tuple(data["board"]["startCorner"]),
    )
    player.consecutive_skips = data["board"]["consecutiveSkips"]
    player.special_captures = {
        kind: data["houseRules"][kind.value]["captured"] for kind in CellKind
    }
    player.rerolls_used = data["houseRules"]["reroll"]["used"]
    player.comeback_nudge_granted = data["houseRules"]["comebackNudge"]["granted"]
    for piece in data["board"]["pieces"]:
        board.place(player, tuple(piece["topLeft"]), piece["width"], piece["height"])
    return player


class ServerGameAdapter:
    def __init__(self, url: str) -> None:
        self.url = url
        self.board = None
        self.players = None
        self.current_player_id = None
        self.state = None
        self.last_roll = None
        self.wildcard_index = None
        self.wildcard_original_roll = None
        self.legal_cache = None
        self.game_over_reason = None
        self.skipped_out_player_id = None
        self.blocked_player_id = None
        self.surrendered_player_id = None
        self.history = None

        self._ws = None
        self._pending_reply: queue.Queue | None = None
        self._connected = threading.Event()

        self._loop = asyncio.new_event_loop()
        # ponytail: daemon=True until close() (a later task) can actually
        # stop the loop cleanly - otherwise a still-running non-daemon
        # thread blocks process/test exit. Flip to non-daemon once close()
        # is wired.
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._connected.wait()

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.create_task(self._connect_and_listen())
        self._loop.run_forever()

    async def _connect_and_listen(self) -> None:
        async with websockets.connect(self.url) as ws:
            self._ws = ws
            async for raw in ws:
                self._handle_message(json.loads(raw))
                self._connected.set()

    def _handle_message(self, data: dict) -> None:
        # ponytail: the received Board/players objects are built fresh and
        # swapped in as whole attributes rather than mutated in place, so a
        # concurrent read from the render thread never sees a half-updated
        # object even without a lock. Add a lock if that stops being true.
        if data["type"] == "state":
            self._apply_state(data["game"])
        pending = self._pending_reply
        if pending is not None and pending.empty():
            pending.put(data)

    def _apply_state(self, data: dict) -> None:
        board = Board(size=data["board"]["size"])
        self.players = {
            int(player_id): _player_from_wire(int(player_id), board, player_data)
            for player_id, player_data in data["players"].items()
        }
        self.board = board

        self.current_player_id = data["turn"]["currentPlayerId"]
        self.state = _TURN_STATE_FROM_WIRE[data["turn"]["turnState"]]
        self.last_roll = tuple(data["turn"]["lastRoll"]) if data["turn"]["lastRoll"] is not None else None
        self.legal_cache = {
            (entry["width"], entry["height"]): {tuple(c) for c in entry["topLefts"]}
            for entry in data["turn"]["legalPlacements"]
        }
        self.wildcard_index = None
        self.wildcard_original_roll = None

        reason = _GAME_OVER_REASON_FROM_WIRE.get(data["gameOver"]["reason"])
        player_id = data["gameOver"]["playerId"]
        self.game_over_reason = reason
        self.skipped_out_player_id = player_id if reason is GameOverReason.SKIP_LIMIT else None
        self.blocked_player_id = player_id if reason is GameOverReason.PLAYER_BLOCKED else None
        self.surrendered_player_id = player_id if reason is GameOverReason.SURRENDER else None

        self.history = []

    def _request(self, msg) -> dict:
        reply_queue: queue.Queue = queue.Queue(maxsize=1)
        self._pending_reply = reply_queue
        try:
            asyncio.run_coroutine_threadsafe(
                self._ws.send(json.dumps(msg.to_json())), self._loop
            ).result()
            return reply_queue.get(timeout=_REQUEST_TIMEOUT)
        finally:
            self._pending_reply = None

    def roll_dice(self) -> tuple[int, int]:
        raise NotImplementedError

    def attempt_place(self, top_left: tuple[int, int], w: int, h: int) -> bool:
        raise NotImplementedError

    def confirm_skip(self) -> None:
        raise NotImplementedError

    def surrender(self) -> None:
        raise NotImplementedError

    def end_turn(self) -> None:
        # The server folds end_turn() into its place/skip handling
        # internally - this stays a permanent local no-op purely so
        # ui/input_common.py's call sites don't need to change.
        pass

    def close(self) -> None:
        raise NotImplementedError
