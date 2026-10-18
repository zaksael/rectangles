import json
from pathlib import Path

import pytest

from rectangles.engine.board import Board
from rectangles.engine.models import Player

# The web client checks its enclosure flood-fill against these boards (frontend/src/game/selfEnclosed.test.ts); regenerate with
# `uv run python tests/engine/enclosure_cases.py` when the rule changes.
CASES = json.loads((Path(__file__).parents[2] / "frontend/src/dev/fixtures/enclosureCases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_the_engine_still_counts_each_stored_board_as_stored(case):
    board = Board(
        size=case["size"],
        wall_edges=frozenset(frozenset(tuple(cell) for cell in wall) for wall in case["walls"]),
        obstacle_cells=frozenset(tuple(cell) for cell in case["obstacles"]),
    )
    players = {1: Player(1, "Player 1", (0, 0)), 2: Player(2, "Player 2", (case["size"] - 1, case["size"] - 1))}
    for r, c, owner in case["owners"]:
        board.place(players[owner], (r, c), 1, 1)

    counts = board.self_enclosed_cell_counts()

    assert {"1": counts.get(1, 0), "2": counts.get(2, 0)} == case["expected"]
