import json
import random

import pytest

from rectangles.engine.analysis import turn_analyses
from rectangles.engine.constants import PLAYER_1, PLAYER_2
from rectangles.engine.game import Game, TurnState
from rectangles.server.app import _bot_turn_step
from rectangles.server.schema import serialize_analysis, serialize_game

ALL_RULES = dict(
    prize_enabled=True,
    walls_enabled=True,
    obstacles_enabled=True,
    pitfall_enabled=True,
    steal_enabled=True,
    wildcard_enabled=True,
    self_enclosed_penalty_enabled=True,
    reroll_enabled=True,
    comeback_nudge_enabled=True,
)
MAX_STEPS = 5000  # a 27x27 game is a few hundred steps; this only stops a stuck loop


# Every difficulty on the smallest board, plus the heaviest board once: a 27x27 game costs ~3s.
@pytest.mark.parametrize(
    ("difficulty", "board_size"),
    [("Basic", 19), ("Greedy", 19), ("Blocking", 19), ("Greedy", 27)],
)
def test_a_full_bot_game_with_every_rule_on_plays_through_and_serializes(difficulty, board_size):
    game = Game(board_size=board_size, rng=random.Random(board_size), **ALL_RULES)

    for step in range(MAX_STEPS):
        if game.state == TurnState.GAME_OVER:
            break
        assert _bot_turn_step(game, difficulty)
        if step % 40 == 0:
            json.dumps(serialize_game(game))
    else:
        pytest.fail(f"game still running after {MAX_STEPS} steps")

    assert game.game_over_reason is not None
    wire = serialize_game(game)
    assert len(wire["gameOver"]["history"]) == len(game.history)
    # The replay of the whole history must land on the live totals.
    final = game.score_breakdown_history()[-1]
    for player_id in (PLAYER_1, PLAYER_2):
        assert final[player_id] == game.score_breakdown(game.players[player_id])
    analyses = turn_analyses(game)
    assert set(analyses) <= set(range(1, len(game.history) + 1))
    json.dumps(serialize_analysis(analyses))
