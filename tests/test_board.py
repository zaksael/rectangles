import pytest

from rectangles.board import Board
from rectangles.models import Player


def make_players(size: int) -> tuple[Player, Player]:
    p1 = Player(1, "Player 1", (0, 0))
    p2 = Player(2, "Player 2", (size - 1, size - 1))
    return p1, p2


def test_can_place_out_of_bounds():
    board = Board(size=6)
    p1, _ = make_players(6)
    assert board.can_place(p1, (0, 0), w=7, h=1) is False  # c+w=7 > 6
    assert board.can_place(p1, (4, 4), w=3, h=1) is False  # c+w=7 > 6
    assert board.can_place(p1, (-1, 0), w=2, h=2) is False


def test_can_place_overlap_rejected():
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (0, 0), w=3, h=3)
    assert board.can_place(p2, (2, 2), w=2, h=2) is False  # overlaps p1's piece


def test_can_place_first_move_wrong_corner_p1():
    board = Board(size=6)
    p1, _ = make_players(6)
    assert board.can_place(p1, (1, 0), w=2, h=2) is False
    assert board.can_place(p1, (0, 1), w=2, h=2) is False


def test_can_place_first_move_correct_corner_p1():
    board = Board(size=6)
    p1, _ = make_players(6)
    assert board.can_place(p1, (0, 0), w=3, h=2) is True


def test_can_place_first_move_correct_corner_p2():
    board = Board(size=6)
    _, p2 = make_players(6)
    # bottom_right must equal (5,5): top_left=(5-h+1, 5-w+1)
    assert board.can_place(p2, (3, 4), w=2, h=3) is True  # bottom_right=(5,5)
    assert board.can_place(p2, (2, 2), w=2, h=2) is False  # fits in bounds but wrong corner


def test_can_place_requires_adjacency_after_first():
    board = Board(size=6)
    p1, _ = make_players(6)
    board.place(p1, (0, 0), w=2, h=2)  # occupies rows0-1, cols0-1
    # Not touching p1's territory at all.
    assert board.can_place(p1, (3, 3), w=2, h=2) is False
    # Shares an edge with p1's territory (right side).
    assert board.can_place(p1, (0, 2), w=2, h=2) is True
    # Shares an edge with p1's territory (below).
    assert board.can_place(p1, (2, 0), w=2, h=2) is True


def test_can_place_adjacency_diagonal_only_rejected():
    board = Board(size=6)
    p1, _ = make_players(6)
    board.place(p1, (0, 0), w=2, h=2)  # occupies rows0-1, cols0-1
    # (2,2) is diagonal to the piece's corner (1,1) only -> no shared edge.
    assert board.can_place(p1, (2, 2), w=2, h=2) is False


def test_can_place_opponent_adjacency_is_fine():
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (0, 0), w=2, h=2)
    board.place(p2, (4, 4), w=2, h=2)  # anchored at p2's corner (5,5)

    # Adjacent only to the opponent's territory, not own -> illegal for p1.
    assert board.can_place(p1, (3, 4), w=1, h=1) is False

    # A p1 piece that touches both its own territory and the opponent's is fine.
    board.place(p1, (0, 2), w=2, h=2)  # touches p1's existing block
    assert board.can_place(p1, (2, 2), w=1, h=2) is True  # touches p1 block above


def test_place_marks_ownership_and_records_piece():
    board = Board(size=6)
    p1, _ = make_players(6)
    rect = board.place(p1, (1, 1), w=2, h=3)

    assert rect.top_left == (1, 1)
    assert rect.width == 2 and rect.height == 3
    assert p1.pieces == [rect]
    for r in range(1, 4):
        for c in range(1, 3):
            assert board.owner_at(r, c) == p1.id
    assert board.is_empty(0, 0) is True


def test_frontier_empty_initially():
    board = Board(size=6)
    p1, _ = make_players(6)
    assert board.frontier(p1) == set()


def test_frontier_correct_after_placement():
    board = Board(size=6)
    p1, _ = make_players(6)
    board.place(p1, (0, 0), w=3, h=3)  # rows0-2, cols0-2
    expected = {(0, 3), (1, 3), (2, 3), (3, 0), (3, 1), (3, 2)}
    assert board.frontier(p1) == expected


def test_frontier_excludes_opponent_and_own_cells():
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (0, 0), w=2, h=2)
    board.place(p2, (0, 2), w=2, h=2)  # adjacent to p1's block, owned by p2
    frontier = board.frontier(p1)
    assert (0, 2) not in frontier  # owned by p2, not empty
    assert (0, 0) not in frontier  # owned by p1 itself
    assert (2, 0) in frontier


def test_board_flag_cells_default_empty():
    board = Board(size=6)
    assert board.flag_cells == frozenset()


def test_board_flag_cells_stored_and_placeable_like_any_empty_cell():
    board = Board(size=6, flag_cells=frozenset({(0, 5), (5, 0)}))
    p1, _ = make_players(6)
    assert board.flag_cells == frozenset({(0, 5), (5, 0)})
    assert board.can_place(p1, (0, 0), w=1, h=1) is True  # flag cells impose no extra restriction


def test_board_wall_edges_default_empty():
    board = Board(size=6)
    assert board.wall_edges == frozenset()


def test_board_wall_edges_block_span_but_not_individual_cells():
    wall = frozenset({frozenset({(2, 2), (3, 2)})})
    board = Board(size=6, wall_edges=wall)
    p1, _ = make_players(6)
    board.place(p1, (2, 1), w=1, h=1)  # adjacent to (2,2); adjacency alone would allow the piece below
    assert board.can_place(p1, (2, 2), w=1, h=2) is False  # piece would straddle the wall
    assert board.is_empty(2, 2) is True  # no cell was sacrificed - both sides stay placeable
    assert board.is_empty(3, 2) is True
    assert board.can_place(p1, (2, 2), w=1, h=1) is True  # the cell itself is still perfectly placeable


def test_board_wall_edges_block_adjacency_across():
    wall = frozenset({frozenset({(2, 2), (3, 2)})})
    board = Board(size=6, wall_edges=wall)
    p1, _ = make_players(6)
    board.place(p1, (2, 2), w=1, h=1)
    assert board.can_place(p1, (3, 2), w=1, h=1) is False  # walled off - doesn't count as adjacent
    assert board.can_place(p1, (2, 3), w=1, h=1) is True  # ordinary (unwalled) adjacency still works


def test_board_wall_edges_excluded_from_frontier():
    wall = frozenset({frozenset({(2, 2), (3, 2)})})
    board = Board(size=6, wall_edges=wall)
    p1, _ = make_players(6)
    board.place(p1, (2, 2), w=1, h=1)
    assert (3, 2) not in board.frontier(p1)
    assert (2, 3) in board.frontier(p1)  # unwalled neighbor still counts


def test_legal_top_lefts_matches_brute_force_can_place():
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (0, 0), w=3, h=2)
    board.place(p2, (4, 4), w=2, h=2)

    w, h = 2, 2
    expected = {
        (r, c)
        for r in range(board.size - h + 1)
        for c in range(board.size - w + 1)
        if board.can_place(p1, (r, c), w, h)
    }
    assert board.legal_top_lefts(p1, w, h) == expected
