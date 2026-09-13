import pytest

from rectangles.engine.board import Board
from rectangles.engine.constants import CellKind
from rectangles.engine.models import Cell, Player, SpecialCell


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


def test_board_special_cells_default_empty():
    board = Board(size=6)
    assert board.special_cells == frozenset()
    assert board.cells_of_kind(CellKind.PRIZE) == frozenset()


def test_board_special_cells_stored_and_placeable_like_any_empty_cell():
    special_cells = frozenset(
        {SpecialCell(CellKind.PRIZE, Cell(0, 5), pair_id=0), SpecialCell(CellKind.PRIZE, Cell(5, 0), pair_id=0)}
    )
    board = Board(size=6, special_cells=special_cells)
    p1, _ = make_players(6)
    assert board.cells_of_kind(CellKind.PRIZE) == frozenset({(0, 5), (5, 0)})
    assert board.can_place(p1, (0, 0), w=1, h=1) is True  # prize cells impose no extra restriction


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


def test_board_obstacle_cells_default_empty():
    board = Board(size=6)
    assert board.obstacle_cells == frozenset()


def test_board_obstacle_cells_block_placement_and_frontier():
    board = Board(size=6, obstacle_cells=frozenset({(2, 2)}))
    p1, _ = make_players(6)
    board.place(p1, (2, 1), w=1, h=1)
    assert board.is_empty(2, 2) is False
    assert board.can_place(p1, (2, 2), w=1, h=1) is False
    assert (2, 2) not in board.frontier(p1)
    assert (2, 3) not in board.frontier(p1)  # not adjacent to any owned cell


def test_board_obstacle_cells_excluded_from_reachable_empty_cells():
    board = Board(size=6, obstacle_cells=frozenset({(0, 1)}))
    p1, _ = make_players(6)
    reachable = board.reachable_empty_cells(p1)
    assert (0, 1) not in reachable


def test_set_obstacle_cells_clears_old_sentinel_and_seeds_new():
    board = Board(size=6, obstacle_cells=frozenset({(1, 1)}))
    board.set_obstacle_cells(frozenset({(3, 3)}))
    assert board.obstacle_cells == frozenset({(3, 3)})
    assert board.is_empty(1, 1) is True  # old obstacle cell released
    assert board.is_empty(3, 3) is False  # new obstacle cell seeded


def test_self_enclosed_cell_counts_credits_hole_bordered_by_one_player_only():
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (1, 2), w=1, h=1)
    board.place(p1, (3, 2), w=1, h=1)
    board.place(p1, (2, 1), w=1, h=1)
    board.place(p1, (2, 3), w=1, h=1)
    # Gives the rest of the board (the "outer" empty region) a second
    # owner, so it isn't wrongly counted as self-enclosed too.
    board.place(p2, (5, 5), w=1, h=1)

    assert board.self_enclosed_cell_counts() == {p1.id: 1}


def test_self_enclosed_cell_counts_ignores_regions_bordered_by_both_players():
    board = Board(size=4)
    p1, p2 = make_players(4)
    board.place(p1, (0, 0), w=1, h=1)
    board.place(p2, (3, 3), w=1, h=1)

    assert board.self_enclosed_cell_counts() == {}


def test_self_enclosed_cell_counts_excludes_regions_touching_the_board_edge():
    # (0, 2) is bordered by only p1 among in-bounds neighbors, but its 4th
    # neighbor is off the top edge - the board edge did part of the
    # enclosing for free, so it must not be penalized.
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (1, 2), w=1, h=1)
    board.place(p1, (0, 1), w=1, h=1)
    board.place(p1, (0, 3), w=1, h=1)
    board.place(p2, (5, 5), w=1, h=1)

    assert board.self_enclosed_cell_counts() == {}


def test_self_enclosed_cell_counts_treats_obstacle_cells_as_neutral():
    # Obstacle-adjacent cell must not count the obstacle as a second
    # "owner" - it should behave like an ordinary boundary, same as a
    # board edge or a wall, not like a third player.
    board = Board(size=6, obstacle_cells=frozenset({(2, 3)}))
    p1, p2 = make_players(6)
    board.place(p1, (1, 2), w=1, h=1)
    board.place(p1, (3, 2), w=1, h=1)
    board.place(p1, (2, 1), w=1, h=1)
    board.place(p2, (5, 5), w=1, h=1)

    assert board.self_enclosed_cell_counts() == {p1.id: 1}


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


def test_reachable_empty_cells_seeds_from_start_corner_before_first_move():
    board = Board(size=6)
    p1, _ = make_players(6)
    reachable = board.reachable_empty_cells(p1)
    assert len(reachable) == 36  # whole empty board, including the opponent's own corner
    assert (0, 0) in reachable
    assert (5, 5) in reachable  # optimistic: reachable-by-either isn't excluded


def test_reachable_empty_cells_expands_past_immediate_frontier():
    board = Board(size=6)
    p1, _ = make_players(6)
    board.place(p1, (0, 0), w=2, h=2)  # frontier is just the 1-cell ring around it
    reachable = board.reachable_empty_cells(p1)
    assert reachable > board.frontier(p1)  # strictly more than the one-hop frontier
    assert (5, 5) in reachable  # nothing blocks the flood-fill from reaching the far corner


def test_reachable_empty_cells_stops_at_opponent_territory():
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (0, 0), w=1, h=1)
    board.place(p2, (0, 3), w=1, h=6)  # entire column 3 - fully seals off columns 4-5
    reachable = board.reachable_empty_cells(p1)
    assert (0, 3) not in reachable  # owned by the opponent, not empty
    assert (0, 2) in reachable  # still open on p1's side
    for r in range(6):
        for c in range(4, 6):
            assert (r, c) not in reachable  # unreachable without crossing p2's territory


def test_reachable_empty_cells_respects_walls():
    # A full-width wall between rows 2 and 3 - no path around it exists, unlike
    # a single short segment the flood-fill could just route past.
    wall = frozenset({frozenset({(2, c), (3, c)}) for c in range(6)})
    board = Board(size=6, wall_edges=wall)
    p1, _ = make_players(6)
    board.place(p1, (2, 2), w=1, h=1)
    reachable = board.reachable_empty_cells(p1)
    assert (2, 3) in reachable  # unwalled neighbor still counts
    for r in range(3, 6):
        for c in range(6):
            assert (r, c) not in reachable  # unreachable on the far side of the wall


def test_reachable_count_if_matches_a_real_placement_then_reverts():
    board = Board(size=6)
    p1, p2 = make_players(6)
    count = board.reachable_count_if(p1.id, p2, (3, 3), 1, 1)
    assert board.is_empty(3, 3)  # stamped-then-reverted, not left behind

    board.place(p1, (3, 3), w=1, h=1)
    assert count == len(board.reachable_empty_cells(p2))


def test_reachable_count_if_captures_a_chokepoint_cutoff():
    # (1, 3) is the sole empty connector into the 4-cell pocket
    # {(0,4), (0,5), (1,4), (1,5)}, walled in on 3 of its 4 sides by p1's
    # placed cells - occupying it should deny the whole pocket, not just
    # itself, even though (1, 3) isn't adjacent to any p2 cell at all.
    board = Board(size=6)
    p1, p2 = make_players(6)
    board.place(p1, (0, 3), w=1, h=1)
    board.place(p1, (2, 4), w=1, h=1)
    board.place(p1, (2, 5), w=1, h=1)
    reachable_before = len(board.reachable_empty_cells(p2))

    denial_chokepoint = reachable_before - board.reachable_count_if(p1.id, p2, (1, 3), 1, 1)
    denial_elsewhere = reachable_before - board.reachable_count_if(p1.id, p2, (3, 5), 1, 1)

    assert denial_chokepoint == 5  # itself + the whole pocket
    assert denial_elsewhere == 1  # just itself, no cutoff
