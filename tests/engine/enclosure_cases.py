"""Writes frontend/src/dev/fixtures/enclosureCases.json: boards with the self-enclosed cell counts the engine computes for them.

The web client re-implements the engine's enclosure flood-fill to hatch the cells (the wire sends only counts), and
frontend/src/game/selfEnclosed.test.ts checks that port against this file. Run from the repo root:
    uv run python tests/engine/enclosure_cases.py
tests/engine/test_enclosure_cases.py checks each stored board still gets its stored counts from the engine.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, ".")
from rectangles.engine.board import Board  # noqa: E402
from rectangles.engine.game import Game, TurnState  # noqa: E402
from rectangles.engine.models import Player  # noqa: E402
from rectangles.server.app import _bot_turn_step  # noqa: E402

OUT = Path("frontend/src/dev/fixtures/enclosureCases.json")


def describe(name: str, board: Board) -> dict:
    owners = [[r, c, board.owner_at(r, c)] for r in range(board.size) for c in range(board.size) if board.owner_at(r, c) in (1, 2)]
    walls = [sorted([list(cell) for cell in edge]) for edge in board.wall_edges]
    counts = board.self_enclosed_cell_counts()
    return {
        "name": name,
        "size": board.size,
        "owners": owners,
        "obstacles": sorted([list(cell) for cell in board.obstacle_cells]),
        "walls": sorted(walls),
        "expected": {"1": counts.get(1, 0), "2": counts.get(2, 0)},
    }


def built(name: str, size: int, pieces, obstacles=(), walls=()) -> dict:
    board = Board(size=size, wall_edges=frozenset(frozenset(w) for w in walls), obstacle_cells=frozenset(obstacles))
    players = {1: Player(1, "Player 1", (0, 0)), 2: Player(2, "Player 2", (size - 1, size - 1))}
    for pid, top_left, w, h in pieces:
        board.place(players[pid], top_left, w, h)
    return describe(name, board)


def ring(pid, r, c):
    """Four pieces around the single cell (r, c)."""
    return [(pid, (r - 1, c - 1), 3, 1), (pid, (r, c - 1), 1, 1), (pid, (r, c + 1), 1, 1), (pid, (r + 1, c - 1), 3, 1)]


def hand_built() -> list[dict]:
    return [
        built("a pocket one player closed off", 7, ring(1, 3, 3)),
        built("a pocket that touches the board edge is exempt", 7, [(1, (1, 2), 3, 1), (1, (0, 2), 1, 1), (1, (0, 4), 1, 1)]),
        built("an obstacle on the rim leaves the pocket enclosed", 7, [(1, (2, 2), 3, 1), (1, (3, 2), 1, 1), (1, (4, 2), 3, 1)], obstacles=[(3, 4)]),
        built("an opponent cell across a wall does not share the pocket", 7, ring(1, 3, 3)[:2] + ring(1, 3, 3)[3:] + [(2, (3, 4), 1, 1)], walls=[((3, 3), (3, 4))]),
        built("a pocket bordering both players is nobody's", 7, ring(1, 3, 3)[:2] + ring(1, 3, 3)[3:] + [(2, (3, 4), 1, 1)]),
        built("each player closes off a pocket", 9, ring(1, 2, 2) + ring(2, 6, 6)),
        built("a pocket of four cells", 9, [(1, (1, 1), 4, 1), (1, (4, 1), 4, 1), (1, (2, 1), 1, 2), (1, (2, 4), 1, 2)]),
    ]


def played(seed: int, stop_at: int | None) -> Game:
    diff = {1: "Greedy", 2: "Blocking"}
    g = Game(
        rng=random.Random(seed), board_size=19, prize_enabled=True, walls_enabled=True, obstacles_enabled=True,
        pitfall_enabled=True, steal_enabled=True, wildcard_enabled=True, self_enclosed_penalty_enabled=True,
        reroll_enabled=True, comeback_nudge_enabled=True,
    )
    while g.state != TurnState.GAME_OVER:
        if stop_at is not None and g.state == TurnState.AWAITING_ROLL and len(g.history) >= stop_at:
            return g
        _bot_turn_step(g, diff[g.current_player_id])
    return g


def real_games() -> list[dict]:
    cases = []
    for seed in (1, 2, 3):
        cases.append(describe(f"a real 19x19 game, seed {seed}, after 25 moves", played(seed, 25).board))
        cases.append(describe(f"a real 19x19 game, seed {seed}, final board", played(seed, None).board))
    return cases


if __name__ == "__main__":
    cases = hand_built() + real_games()
    OUT.write_text(json.dumps(cases, indent=1) + "\n")
    print(f"wrote {OUT}: {len(cases)} boards; expected counts:")
    for c in cases:
        print(f"  {c['expected']['1']:>3} {c['expected']['2']:>3}  {c['name']}")
