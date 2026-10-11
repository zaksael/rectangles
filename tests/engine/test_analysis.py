from rectangles.engine.analysis import (
    AnalysisAxis,
    AxisBreakdown,
    Candidate,
    TurnAnalysis,
    candidate_pool,
    full_axes,
    partial_axes,
    ranking_value,
    turn_analyses,
)
from rectangles.engine.constants import PLAYER_1, PLAYER_2, CellKind
from rectangles.engine.game import Game
from rectangles.engine.models import Cell, Rectangle, SpecialCell, TurnRecord


def _special(kind: CellKind, *cells: tuple[int, int]) -> frozenset[SpecialCell]:
    return frozenset(SpecialCell(kind, Cell(*cell), pair_id=i) for i, cell in enumerate(cells))


def test_candidate_pool_is_both_orientations_of_the_rolled_pair():
    # P1's first move is anchored at the start corner, so each orientation has one top-left.
    game = Game(board_size=6)
    record = TurnRecord(PLAYER_1, roll=(1, 4), placed=Rectangle((0, 0), 1, 4, PLAYER_1))

    pool = candidate_pool(record, game.board, game.players[PLAYER_1])

    assert set(pool) == {Candidate((0, 0), 1, 4), Candidate((0, 0), 4, 1)}


def test_candidate_pool_spans_every_wildcard_value():
    # Doubles (2,2) wildcard-edited to 1: the fixed die stays 2, the other takes any of 1..6.
    game = Game(board_size=6, wildcard_enabled=True)
    record = TurnRecord(
        PLAYER_1, roll=(2, 1), placed=Rectangle((0, 0), 2, 1, PLAYER_1), wildcard_original_roll=(2, 2)
    )

    pool = candidate_pool(record, game.board, game.players[PLAYER_1])

    sizes = {(c.width, c.height) for c in pool}
    assert sizes == {(2, 1), (1, 2), (2, 2), (2, 3), (3, 2), (2, 4), (4, 2), (2, 5), (5, 2), (2, 6), (6, 2)}


def test_partial_axes_count_prize_cells_under_a_candidate():
    game = Game(board_size=6, prize_enabled=True)
    game.board.special_cells = _special(CellKind.PRIZE, (0, 3))
    player, opponent = game.players[PLAYER_1], game.players[PLAYER_2]
    reachable_before = len(game.board.reachable_empty_cells(opponent))

    along_row = partial_axes(game, game.board, player, opponent, Candidate((0, 0), 4, 1), reachable_before)
    down_column = partial_axes(game, game.board, player, opponent, Candidate((0, 0), 1, 4), reachable_before)

    assert (along_row.prize_cells, along_row.pitfall_cells, along_row.enclosure_delta) == (1, 0, 0)
    assert down_column.prize_cells == 0


def test_ranking_value_weights_prize_points_and_adds_denial_at_one():
    game = Game(board_size=6, prize_enabled=True)
    axes = AxisBreakdown(prize_cells=2, pitfall_cells=1, denial_cells=7, enclosure_delta=0)

    expected = 2 * game.points_for(CellKind.PRIZE) - game.points_for(CellKind.PITFALL) + 7
    assert ranking_value(game, axes) == 2 * 10 - 10 + 7 == expected


def _first_move(game, roll, rect):
    game.history = [TurnRecord(PLAYER_1, roll=roll, placed=Rectangle(*rect, PLAYER_1))]


def test_turn_analyses_is_empty_for_a_game_with_no_moves():
    assert turn_analyses(Game(board_size=6)) == {}


def test_turn_analyses_never_flags_a_skip():
    game = Game(board_size=6)
    game.history = [TurnRecord(PLAYER_1, roll=(6, 6), placed=None)]

    assert turn_analyses(game) == {}


def test_turn_analyses_flags_a_missed_prize_capture():
    # P1's first move is anchored at (0, 0): the two candidates are the 1x4 / 4x1 swap.
    # The chosen 1x4 strip down column 0 misses the prize at (0, 3); the 4x1 strip along row 0 takes it.
    game = Game(board_size=6, prize_enabled=True)
    game.board.special_cells = _special(CellKind.PRIZE, (0, 3))
    _first_move(game, (1, 4), ((0, 0), 1, 4))

    assert turn_analyses(game) == {1: TurnAnalysis(AnalysisAxis.PRIZE, 0, 10, Candidate((0, 0), 4, 1))}


def test_turn_analyses_flags_a_hit_pitfall_the_other_orientation_avoids():
    game = Game(board_size=6)
    game.pitfall_enabled = True
    game.board.special_cells = _special(CellKind.PITFALL, (0, 3))
    _first_move(game, (1, 4), ((0, 0), 4, 1))

    assert turn_analyses(game) == {1: TurnAnalysis(AnalysisAxis.PITFALL, -10, 0, Candidate((0, 0), 1, 4))}


def test_turn_analyses_names_the_axis_with_the_larger_weighted_gap():
    # Chosen 1x4 misses a 20-point prize at (0, 3) and hits a pitfall at (2, 0); the 4x1 does the opposite.
    # Points combine (-10 vs 20) but the label names the bigger contributor, the prize.
    game = Game(board_size=6, prize_enabled=True, special_cell_points={"prize": 20})
    game.board.special_cells = _special(CellKind.PRIZE, (0, 3)) | _special(CellKind.PITFALL, (2, 0))
    game.pitfall_enabled = True
    _first_move(game, (1, 4), ((0, 0), 1, 4))

    assert turn_analyses(game) == {1: TurnAnalysis(AnalysisAxis.PRIZE, -10, 20, Candidate((0, 0), 4, 1))}


def test_turn_analyses_ignores_leftover_pitfall_cells_when_the_rule_is_off():
    game = Game(board_size=6)
    game.board.special_cells = _special(CellKind.PITFALL, (0, 3))
    _first_move(game, (1, 4), ((0, 0), 4, 1))

    assert turn_analyses(game) == {}


def test_turn_analyses_flags_a_missed_denial_in_cells():
    # (1, 3) is a chokepoint: occupying it cuts P2 off from a 4-cell pocket without touching P2's frontier.
    # The played move at (3, 5) denies only itself.
    game = Game(board_size=6)
    game.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((0, 3), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 4), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 5), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((3, 5), 1, 1, PLAYER_1)),
    ]

    # Sparse: only the mistake has a key.
    assert turn_analyses(game) == {4: TurnAnalysis(AnalysisAxis.DENIAL, 1, 5, Candidate((1, 3), 1, 1))}


def test_turn_analyses_flags_a_self_created_enclosure():
    # A wall cuts P2 off from rows 0-3, so sealing the ring around (2, 2) earns no extra denial credit
    # and the enclosure penalty alone decides.
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    game.board.wall_edges = frozenset({frozenset({(3, c), (4, c)}) for c in range(6)})
    game.history = [
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((5, 5), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((1, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((3, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 3), 1, 1, PLAYER_1)),
    ]

    assert turn_analyses(game) == {5: TurnAnalysis(AnalysisAxis.ENCLOSURE, -1, 0, Candidate((3, 1), 1, 1))}


def test_turn_analyses_does_not_flag_a_forced_move():
    # The closing 2x2 has exactly one legal position, so sealing a hole with it was unavoidable.
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    p2_cell = (5, 5)
    empties = {(2, 2), (2, 3), (2, 4), (2, 5), (3, 4), (3, 5)}
    history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((r, c), 1, 1, PLAYER_1))
        for r in range(6)
        for c in range(6)
        if (r, c) not in empties and (r, c) != p2_cell
    ]
    history.append(TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle(p2_cell, 1, 1, PLAYER_2)))
    history.append(TurnRecord(PLAYER_1, roll=(2, 2), placed=Rectangle((2, 4), 2, 2, PLAYER_1)))
    game.history = history

    assert len(history) not in turn_analyses(game)


def test_turn_analyses_flags_a_suboptimal_wildcard_pick():
    # Doubles (2, 2) edited down to 1: the chosen 2x1 cannot reach the prize at (0, 3); a 6x2 can, and denies most.
    game = Game(board_size=6, prize_enabled=True, wildcard_enabled=True)
    game.board.special_cells = _special(CellKind.PRIZE, (0, 3))
    game.history = [
        TurnRecord(
            PLAYER_1, roll=(2, 1), placed=Rectangle((0, 0), 1, 2, PLAYER_1), wildcard_original_roll=(2, 2)
        )
    ]

    assert turn_analyses(game) == {1: TurnAnalysis(AnalysisAxis.PRIZE, 0, 10, Candidate((0, 0), 6, 2))}


def test_turn_analyses_leaves_an_optimal_wildcard_pick_unflagged():
    game = Game(board_size=6, prize_enabled=True, wildcard_enabled=True)
    game.board.special_cells = _special(CellKind.PRIZE, (0, 3))
    game.history = [
        TurnRecord(
            PLAYER_1, roll=(2, 6), placed=Rectangle((0, 0), 6, 2, PLAYER_1), wildcard_original_roll=(2, 2)
        )
    ]

    assert turn_analyses(game) == {}


def test_turn_analyses_anchors_the_second_player_at_their_real_corner():
    # P2's first move belongs at (5, 5); a wrong anchor would leave the pool empty or mismatched.
    game = Game(board_size=6)
    game.history = [
        TurnRecord(PLAYER_1, roll=(2, 2), placed=Rectangle((0, 0), 2, 2, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(3, 3), placed=Rectangle((3, 3), 3, 3, PLAYER_2)),
    ]

    assert 2 not in turn_analyses(game)


def test_turn_analyses_pruned_search_matches_an_exhaustive_scan():
    # Enclosure + Wildcard is where the ceiling prune applies; the winner must be the one a full scan finds.
    game = Game(board_size=6, prize_enabled=True, wildcard_enabled=True, self_enclosed_penalty_enabled=True)
    game.board.special_cells = _special(CellKind.PRIZE, (0, 3), (3, 0))
    game.board.wall_edges = frozenset({frozenset({(3, c), (4, c)}) for c in range(6)})
    record = TurnRecord(
        PLAYER_1, roll=(2, 1), placed=Rectangle((0, 0), 2, 1, PLAYER_1), wildcard_original_roll=(2, 2)
    )
    game.history = [record]

    player, opponent = game.players[PLAYER_1], game.players[PLAYER_2]
    reachable_before = len(game.board.reachable_empty_cells(opponent))
    pool = candidate_pool(record, game.board, player)
    values = {
        c: ranking_value(game, full_axes(game, game.board, player, opponent, c, reachable_before, 0))
        for c in pool
    }
    best_value = max(values.values())
    analysis = turn_analyses(game)[1]

    assert values[analysis.better] == best_value
