import pytest

from rectangles.constants import (
    FLAG_CELL_PAIRS,
    MIN_SPECIAL_CELL_DISTANCE,
    OBSTACLE_CELL_PAIRS,
    PLAYER_1,
    PLAYER_2,
    REROLL_LIMIT,
    SELF_ENCLOSED_PENALTY_PER_CELL,
    START_CORNER_EXCLUSION_RADIUS,
    WALL_LINE_LENGTH,
    WALL_LINE_PAIRS,
)
from rectangles.game import Game, GameOverReason, TurnState


class ScriptedRandom:
    """Stand-in for random.Random that returns a fixed, ordered sequence."""

    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def test_deterministic_roll_via_injected_rng():
    game = Game(rng=ScriptedRandom([4, 6]))
    assert game.roll_dice() == (4, 6)


def test_turn_alternates_after_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.attempt_place((0, 0), 2, 3) is True

    if not game.check_game_over():
        game.end_turn()

    assert game.current_player_id == PLAYER_2
    assert game.state == TurnState.AWAITING_ROLL


def test_skip_when_no_legal_move():
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty

    game.roll_dice()

    assert game.state == TurnState.SKIPPED
    assert game.last_roll == (6, 6)


def test_double_without_wildcard_enabled_turn_alternates_normally():
    # No more standalone doubles rule: without wildcard_enabled, a double is
    # just an ordinary roll and the turn still alternates.
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.attempt_place((0, 0), 2, 2) is True

    if not game.check_game_over():
        game.end_turn()

    assert game.current_player_id == PLAYER_2


def test_repeated_skips_reach_skip_limit():
    game = Game(board_size=4, skip_limit=2, rng=ScriptedRandom([6, 6, 6, 6, 6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty; a 6x6 never fits

    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert p1.consecutive_skips == 1
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2

    game.roll_dice()  # p2, also stuck at their unmoved start corner (3, 3)
    assert game.state == TurnState.SKIPPED
    assert p1.consecutive_skips == 1  # p2's skip doesn't touch p1's streak
    game.end_turn()
    assert game.current_player_id == PLAYER_1

    game.roll_dice()
    assert p1.consecutive_skips == 2
    assert game.check_game_over() is True
    assert game.game_over_reason == GameOverReason.SKIP_LIMIT
    assert game.skipped_out_player_id == PLAYER_1


def test_attempt_place_rejects_illegal_top_left():
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()

    assert game.attempt_place((3, 3), 2, 2) is False  # not anchored at p1's start corner

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.history == []


def test_attempt_place_rejects_wrong_state():
    game = Game(board_size=6)
    assert game.state == TurnState.AWAITING_ROLL

    assert game.attempt_place((0, 0), 1, 1) is False

    assert game.history == []


def test_roll_dice_raises_outside_awaiting_roll():
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT

    with pytest.raises(ValueError):
        game.roll_dice()


def test_end_turn_is_noop_after_game_over():
    game = Game(board_size=4)
    game.state = TurnState.GAME_OVER
    game.current_player_id = PLAYER_1

    game.end_turn()

    assert game.state == TurnState.GAME_OVER
    assert game.current_player_id == PLAYER_1


def test_surrender_ends_game_with_opponent_as_winner():
    game = Game(board_size=8)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=5, h=5)  # p1 has far more area
    game.board.place(p2, (7, 7), w=1, h=1)

    game.surrender()  # current_player_id is PLAYER_1

    assert game.state == TurnState.GAME_OVER
    assert game.game_over_reason == GameOverReason.SURRENDER
    assert game.surrendered_player_id == PLAYER_1
    assert game.winner() == PLAYER_2  # opponent wins despite having less area


def test_surrender_is_noop_after_game_over():
    game = Game(board_size=4)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL

    game.surrender()

    assert game.game_over_reason == GameOverReason.BOARD_FULL
    assert game.surrendered_player_id is None


def test_placement_appends_history_record():
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True

    assert len(game.history) == 1
    record = game.history[0]
    assert record.player_id == PLAYER_1
    assert record.roll == (2, 2)
    assert record.placed is not None
    assert (record.placed.top_left, record.placed.width, record.placed.height) == ((0, 0), 2, 2)


def test_skip_appends_history_record():
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty

    game.roll_dice()

    assert len(game.history) == 1
    record = game.history[0]
    assert record.player_id == PLAYER_1
    assert record.roll == (6, 6)
    assert record.placed is None


def test_reset_clears_history():
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    game.attempt_place((0, 0), 2, 2)
    assert len(game.history) == 1

    game.reset()

    assert game.history == []


def test_reset_restores_initial_state():
    game = Game(board_size=4, skip_limit=2)
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=1, h=1)
    p1.consecutive_skips = 2
    assert game.check_game_over() is True
    assert game.game_over_reason == GameOverReason.SKIP_LIMIT
    assert game.skipped_out_player_id == PLAYER_1

    game.reset()

    assert game.state == TurnState.AWAITING_ROLL
    assert game.current_player_id == PLAYER_1
    assert game.last_roll is None
    assert game.legal_cache == {}
    assert game.game_over_reason is None
    assert game.skipped_out_player_id is None
    assert game.blocked_player_id is None
    assert game.history == []
    assert game.players[PLAYER_1].pieces == []
    assert game.players[PLAYER_1].consecutive_skips == 0


def test_game_over_detection_after_placement():
    # Every roll here is (1,1), the only piece shape that leaves a 2x2 board
    # exactly evenly split between the two players' corners.
    game = Game(board_size=2, rng=ScriptedRandom([1, 1, 1, 1, 1, 1, 1, 1]))

    game.roll_dice()
    assert game.attempt_place((0, 0), 1, 1) is True  # p1 anchors at (0,0)
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2

    game.roll_dice()
    assert game.attempt_place((1, 1), 1, 1) is True  # p2 anchors at (1,1)
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_1

    game.roll_dice()
    assert game.attempt_place((0, 1), 1, 1) is True  # p1 claims (0,1)
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2

    game.roll_dice()
    assert game.attempt_place((1, 0), 1, 1) is True  # p2 claims the last cell
    assert game.check_game_over() is True
    assert game.state == TurnState.GAME_OVER


def test_board_full_reports_board_full_reason():
    # See test_game_over_detection_after_placement for why every roll is (1,1).
    game = Game(board_size=2, rng=ScriptedRandom([1, 1, 1, 1, 1, 1, 1, 1]))
    game.roll_dice()
    game.attempt_place((0, 0), 1, 1)
    game.end_turn()
    game.roll_dice()
    game.attempt_place((1, 1), 1, 1)
    game.end_turn()
    game.roll_dice()
    game.attempt_place((0, 1), 1, 1)
    game.end_turn()
    game.roll_dice()
    game.attempt_place((1, 0), 1, 1)

    assert game.check_game_over() is True
    assert game.game_over_reason == GameOverReason.BOARD_FULL


def test_game_over_detection_after_skip():
    game = Game(board_size=2, rng=ScriptedRandom([3, 3]))
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=2)
    game.board.place(p2, (0, 1), w=1, h=2)  # board fully filled

    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert game.check_game_over() is True


def test_game_over_when_player_fully_blocked():
    game = Game(board_size=4)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=1)
    game.board.place(p2, (1, 0), w=1, h=1)  # seals p1's south neighbor
    game.board.place(p2, (0, 1), w=1, h=1)  # seals p1's east neighbor
    # Plenty of empty cells remain, including p2's own start corner (3, 3).

    assert game.check_game_over() is True
    assert game.state == TurnState.GAME_OVER
    assert game.game_over_reason == GameOverReason.PLAYER_BLOCKED
    assert game.blocked_player_id == PLAYER_1


def test_no_blocked_game_over_before_first_move():
    game = Game(board_size=4)
    p2 = game.players[PLAYER_2]
    game.board.place(p2, (3, 3), w=1, h=1)  # p2 has moved, p1 has not

    assert game.check_game_over() is False


def test_flag_conquest_disabled_by_default_no_flags_and_score_equals_area():
    game = Game(board_size=8)
    p1 = game.players[PLAYER_1]
    assert game.board.flag_cells == frozenset()

    game.board.place(p1, (0, 0), w=2, h=2)  # area 4

    assert p1.flags_captured == 0
    assert game.total_score(p1) == p1.total_area == 4


def test_reset_computes_symmetric_randomized_flags_for_odd_board_sizes():
    for size in (11, 19):
        game = Game(board_size=size, flag_conquest_enabled=True)
        flags = game.board.flag_cells
        assert len(flags) <= 2 * FLAG_CELL_PAIRS

        def mirror(cell: tuple[int, int]) -> tuple[int, int]:
            r, c = cell
            return (size - 1 - r, size - 1 - c)

        assert {mirror(c) for c in flags} == flags  # 180-degree symmetric, neither player favored

        corners = ((0, 0), (size - 1, size - 1))
        for r, c in flags:
            assert all(
                max(abs(r - cr), abs(c - cc)) > START_CORNER_EXCLUSION_RADIUS for cr, cc in corners
            )


def test_flag_cells_empty_when_board_too_small_for_any_candidate():
    # size=6: every cell is within START_CORNER_EXCLUSION_RADIUS (5) of one
    # of the two start corners, same degenerate case Walls/Obstacles already
    # hit on this board size - both flag pairs are skipped, not errored.
    game = Game(board_size=6, flag_conquest_enabled=True)
    assert game.board.flag_cells == frozenset()


def test_flag_cells_never_includes_the_self_mirroring_center_cell():
    # The exact center of an odd board mirrors to itself; picking it as one
    # end of a pair would silently produce an unpaired flag. A ScriptedRandom
    # that always picks candidate index 0 exercises whichever candidate list
    # ordering is used - the center cell must never appear regardless.
    for size in (11, 19):
        game = Game(board_size=size, flag_conquest_enabled=True, rng=ScriptedRandom([0, 0]))
        flags = game.board.flag_cells
        center = (size // 2, size // 2)
        assert center not in flags
        assert len(flags) % 2 == 0  # every flag has its mirror present too


def _chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def test_flag_and_obstacle_cells_respect_min_special_cell_distance():
    # Every pair of distinct cells from the same feature - including a cell
    # and its own mirror - must be at least MIN_SPECIAL_CELL_DISTANCE apart,
    # so a feature's own cells spread across the board instead of
    # clustering. Real (unscripted) rng across many draws: this is a
    # property of the candidate filtering, not of one specific rng sequence.
    for _ in range(30):
        game = Game(board_size=19, flag_conquest_enabled=True, obstacles_enabled=True)
        for cells in (list(game.board.flag_cells), list(game.board.obstacle_cells)):
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    assert _chebyshev(cells[i], cells[j]) >= MIN_SPECIAL_CELL_DISTANCE


def test_walls_disabled_by_default():
    game = Game(board_size=11)
    assert game.board.wall_edges == frozenset()


def test_reset_computes_symmetric_randomized_walls_for_odd_board_sizes():
    for size in (11, 19):
        for kwargs in ({}, {"flag_conquest_enabled": True}):
            game = Game(board_size=size, walls_enabled=True, **kwargs)
            edges = game.board.wall_edges
            assert edges != frozenset()
            # At most WALL_LINE_PAIRS pairs, each pair contributing two
            # WALL_LINE_LENGTH-long lines (the segment plus its mirror).
            assert len(edges) <= 2 * WALL_LINE_PAIRS * WALL_LINE_LENGTH

            def mirror(cell: tuple[int, int]) -> tuple[int, int]:
                r, c = cell
                return (size - 1 - r, size - 1 - c)

            mirrored = {frozenset(mirror(c) for c in edge) for edge in edges}
            assert mirrored == edges  # 180-degree symmetric, so neither player is favored

            touched_cells = {cell for edge in edges for cell in edge}

            # No wall cell lands within START_CORNER_EXCLUSION_RADIUS of
            # either player's starting corner.
            corners = ((0, 0), (size - 1, size - 1))
            for r, c in touched_cells:
                assert all(
                    max(abs(r - cr), abs(c - cc)) > START_CORNER_EXCLUSION_RADIUS for cr, cc in corners
                )

            # Walls never overlap flag cells when both modes are enabled.
            assert not (touched_cells & game.board.flag_cells)


def _wall_segments(edges: frozenset) -> list[list[tuple[int, int]]]:
    # Group individual 2-cell unit edges into contiguous segments (cells
    # within one segment are Chebyshev-adjacent by construction) so
    # cross-segment distance can be checked without tripping on a segment's
    # own internal adjacency.
    cells = list({cell for edge in edges for cell in edge})
    parent = {cell: cell for cell in cells}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            if _chebyshev(cells[i], cells[j]) <= 1:
                parent[find(cells[i])] = find(cells[j])

    groups: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for cell in cells:
        groups.setdefault(find(cell), []).append(cell)
    return list(groups.values())


def test_wall_segments_respect_min_special_cell_distance():
    # Different wall segments - including a segment and its own mirror -
    # must stay MIN_SPECIAL_CELL_DISTANCE apart, so Walls' own segments
    # spread across the board instead of clustering.
    for _ in range(20):
        game = Game(board_size=19, walls_enabled=True)
        segments = _wall_segments(game.board.wall_edges)
        for i in range(len(segments)):
            for j in range(i + 1, len(segments)):
                best = min(_chebyshev(a, b) for a in segments[i] for b in segments[j])
                assert best >= MIN_SPECIAL_CELL_DISTANCE


def test_obstacles_disabled_by_default():
    game = Game(board_size=11)
    assert game.board.obstacle_cells == frozenset()


def test_reset_computes_symmetric_randomized_obstacles_for_odd_board_sizes():
    for size in (11, 19):
        for kwargs in ({}, {"flag_conquest_enabled": True}, {"walls_enabled": True}):
            game = Game(board_size=size, obstacles_enabled=True, **kwargs)
            cells = game.board.obstacle_cells
            assert cells != frozenset()
            assert len(cells) <= 2 * OBSTACLE_CELL_PAIRS

            def mirror(cell: tuple[int, int]) -> tuple[int, int]:
                r, c = cell
                return (size - 1 - r, size - 1 - c)

            assert {mirror(c) for c in cells} == cells  # 180-degree symmetric

            corners = ((0, 0), (size - 1, size - 1))
            for r, c in cells:
                assert all(
                    max(abs(r - cr), abs(c - cc)) > START_CORNER_EXCLUSION_RADIUS for cr, cc in corners
                )

            # Never overlaps flag cells or wall-touched cells when those modes are also on.
            assert not (cells & game.board.flag_cells)
            wall_cells = {cell for edge in game.board.wall_edges for cell in edge}
            assert not (cells & wall_cells)


def test_attempt_place_captures_single_flag():
    # First move anchored at p1's start corner (0,0): a 6x6 piece (max dice
    # value) reaches from (0,0) to (5,5).
    # flag_conquest_enabled stays False at construction to skip random
    # generation (and its rng consumption); flipped True with flag_cells set
    # directly so the capture is deterministic.
    game = Game(board_size=11, rng=ScriptedRandom([6, 6]))
    game.flag_conquest_enabled = True
    game.board.flag_cells = frozenset({(0, 10), (10, 0), (5, 5)})
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]

    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True

    assert p1.flags_captured == 1
    assert p2.flags_captured == 0


def test_attempt_place_captures_two_flags_in_one_placement():
    # flag_conquest_enabled stays False at construction to skip random
    # generation (and its rng consumption); flipped True with flag_cells set
    # directly so the captures are deterministic.
    game = Game(board_size=11, rng=ScriptedRandom([5, 6, 1, 1, 6, 6]))
    game.flag_conquest_enabled = True
    game.board.flag_cells = frozenset({(0, 10), (10, 0), (5, 5)})
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]

    # P1's first move: anchored at (0,0), covers rows0-5/cols0-4 - no flags,
    # but leaves column 4 owned so a later piece can be adjacent to it.
    game.roll_dice()
    assert game.attempt_place((0, 0), 5, 6) is True
    assert p1.flags_captured == 0
    assert game.check_game_over() is False
    game.end_turn()

    # P2's first move: a 1x1 at its own start corner, unrelated to any flag.
    game.roll_dice()
    assert game.attempt_place((10, 10), 1, 1) is True
    assert p2.flags_captured == 0
    assert game.check_game_over() is False
    game.end_turn()

    # P1's second move: a 6x6 piece at (0,5), edge-adjacent to the column-4
    # territory from turn 1, spans rows0-5/cols5-10 - covering both the
    # (0,10) corner flag and the (5,5) center flag in a single placement.
    game.roll_dice()
    assert game.attempt_place((0, 5), 6, 6) is True

    assert p1.flags_captured == 2
    assert p2.flags_captured == 0


def test_total_score_can_decide_a_winner_area_alone_would_not():
    game = Game(board_size=8, flag_conquest_enabled=True, flag_bonus_points=5)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=5, h=2)  # area 10
    game.board.place(p2, (6, 4), w=4, h=2)  # area 8
    p2.flags_captured = 1  # total_score: 8 + 1*5 = 13

    assert p1.total_area > p2.total_area  # area alone would favor p1
    assert game.winner() == PLAYER_2  # but the flag bonus decides it


def test_potential_stats_area_and_flag_points():
    game = Game(board_size=4, flag_conquest_enabled=True, flag_bonus_points=7)
    p1 = game.players[PLAYER_1]
    game.board.flag_cells = frozenset({(0, 1), (3, 2)})
    game.board.place(p1, (0, 0), w=1, h=1)

    stats = game.potential_stats(p1)

    assert stats["area"] == 15  # every other cell on the 4x4 board is still open
    assert stats["flag_points"] == 14  # both reachable flags, 2 * flag_bonus_points(7)


def test_potential_stats_excludes_already_captured_flags():
    game = Game(board_size=4, flag_conquest_enabled=True, flag_bonus_points=7)
    p1 = game.players[PLAYER_1]
    game.board.flag_cells = frozenset({(0, 1)})
    game.board.place(p1, (0, 0), w=2, h=1)  # covers (0,0) and (0,1), capturing the flag
    p1.flags_captured = 1

    stats = game.potential_stats(p1)

    assert stats["flag_points"] == 0  # already captured cell isn't empty anymore, so it drops out


def test_surrender_winner_unaffected_by_flag_bonus():
    game = Game(board_size=8, flag_conquest_enabled=True, flag_bonus_points=100)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=5, h=5)
    p1.flags_captured = 3  # would dominate on score alone

    game.surrender()  # current_player_id is PLAYER_1

    assert game.winner() == PLAYER_2  # opponent wins regardless of score


def test_winner_area_sum():
    game = Game(board_size=8)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=3, h=2)  # area 6
    game.board.place(p2, (6, 6), w=2, h=2)  # area 4
    assert game.winner() == PLAYER_1


def test_tie_returns_none():
    game = Game(board_size=8)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=2, h=2)  # area 4
    game.board.place(p2, (6, 6), w=2, h=2)  # area 4
    assert game.winner() is None


def test_degenerate_1x1_board_immediate_gameover():
    game = Game(board_size=1, rng=ScriptedRandom([1, 1]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.attempt_place((0, 0), 1, 1) is True
    assert game.check_game_over() is True
    assert game.winner() == PLAYER_1


def test_skip_increments_consecutive_skips():
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    assert p1.consecutive_skips == 0

    game.roll_dice()

    assert game.state == TurnState.SKIPPED
    assert p1.consecutive_skips == 1


def test_placement_resets_consecutive_skips():
    game = Game(board_size=4, rng=ScriptedRandom([2, 2]))
    p1 = game.players[PLAYER_1]
    p1.consecutive_skips = 2

    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True

    assert p1.consecutive_skips == 0


def test_game_over_triggers_at_skip_limit():
    game = Game(board_size=8, skip_limit=3)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=1)
    game.board.place(p2, (7, 7), w=1, h=1)
    p1.consecutive_skips = 3

    assert game.check_game_over() is True
    assert game.state == TurnState.GAME_OVER
    assert game.game_over_reason == GameOverReason.SKIP_LIMIT
    assert game.skipped_out_player_id == PLAYER_1


def test_game_over_not_triggered_below_skip_limit():
    game = Game(board_size=8, skip_limit=3)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=1)
    game.board.place(p2, (7, 7), w=1, h=1)
    p1.consecutive_skips = 2

    assert game.check_game_over() is False
    assert game.state != TurnState.GAME_OVER


def test_skip_limit_configurable_via_constructor():
    game = Game(board_size=8, skip_limit=1)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=1)
    game.board.place(p2, (7, 7), w=1, h=1)
    p1.consecutive_skips = 1

    assert game.check_game_over() is True
    assert game.game_over_reason == GameOverReason.SKIP_LIMIT


def test_skip_streak_isolated_per_player():
    # p2's own start corner (its only possible anchor, since it hasn't moved)
    # is pre-occupied so every one of its rolls is an unconditional skip
    # regardless of dice value.
    game = Game(board_size=4, skip_limit=2, rng=ScriptedRandom([1, 2, 3, 5, 2, 1, 1, 3]))
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (3, 3), w=1, h=1)

    # Turn 1: p1 rolls (1,2) and places adjacent to its own (3,3) cell.
    game.roll_dice()
    assert game.attempt_place((1, 3), 1, 2) is True
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2

    # Turn 2: p2 rolls (3,5) - its start corner (3,3) is already taken, so
    # it can never place anything, regardless of the roll.
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert p2.consecutive_skips == 1
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_1

    # Turn 3: p1 rolls (2,1) and places again - p1's own streak (already 0)
    # is unaffected by p2's skip.
    game.roll_dice()
    assert game.attempt_place((1, 1), 2, 1) is True
    assert p1.consecutive_skips == 0
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2

    # Turn 4: p2 rolls (1,3) - still permanently blocked, second consecutive
    # skip for p2 hits skip_limit=2, ending the game. p1's streak is untouched.
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert p2.consecutive_skips == 2
    assert p1.consecutive_skips == 0

    assert game.check_game_over() is True
    assert game.game_over_reason == GameOverReason.SKIP_LIMIT
    assert game.skipped_out_player_id == PLAYER_2


def test_wildcard_disabled_by_default_never_triggers():
    game = Game(rng=ScriptedRandom([4, 6]))
    assert game.roll_dice() == (4, 6)
    assert game.wildcard_enabled is False
    assert game.wildcard_index is None
    assert game.state == TurnState.CHOOSING_PLACEMENT


def test_wildcard_not_triggered_on_a_non_double_roll():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([3, 5]))
    assert game.roll_dice() == (3, 5)
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.wildcard_index is None


def test_wildcard_triggers_and_lets_player_edit_one_number():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([5, 5, 0]))
    assert game.roll_dice() == (5, 5)
    assert game.state == TurnState.CHOOSING_WILDCARD
    assert game.wildcard_index == 0
    assert game.wildcard_original_roll == (5, 5)

    game.choose_wildcard_value(6)
    assert game.last_roll == (6, 5)
    assert game.wildcard_index is None
    assert game.state == TurnState.CHOOSING_PLACEMENT


def test_wildcard_edit_can_produce_a_skip():
    game = Game(board_size=4, wildcard_enabled=True, rng=ScriptedRandom([3, 3, 1]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    game.choose_wildcard_value(6)  # edits index 1: (3, 3) -> (3, 6), too tall for a 4x4 board either way
    assert game.last_roll == (3, 6)
    assert game.state == TurnState.SKIPPED


def test_wildcard_skips_the_picker_when_every_value_is_illegal():
    # Fixed die stays 6, which never fits on a 4x4 board regardless of what
    # the wildcard die becomes - forcing a click through an all-illegal
    # picker would be a pointless extra step, so roll_dice() should resolve
    # straight to the skip instead of entering CHOOSING_WILDCARD at all.
    game = Game(board_size=4, wildcard_enabled=True, rng=ScriptedRandom([6, 6, 1]))
    game.roll_dice()

    assert game.state == TurnState.SKIPPED
    assert game.wildcard_index is None
    assert game.history[-1].wildcard_original_roll == (6, 6)


def test_legal_placements_for_value_substitutes_the_wildcard_die():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([5, 5, 0]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD
    assert game.wildcard_index == 0  # index 0 (first die) is the one still editable

    placements = game.legal_placements_for_value(3)

    assert set(placements) == {(3, 5), (5, 3)}
    assert placements[(3, 5)] == game.board.legal_top_lefts(game.current_player, 3, 5)
    assert placements[(5, 3)] == game.board.legal_top_lefts(game.current_player, 5, 3)


def test_wildcard_resolution_does_not_grant_a_bonus_turn():
    # Doubles no longer grant an extra turn - this was fully replaced by the
    # merged Wildcard Roll trigger, not kept alongside it.
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([3, 3, 1]))
    game.roll_dice()
    assert game.wildcard_index == 1

    game.choose_wildcard_value(5)  # (3, 3) -> (3, 5)
    assert game.last_roll == (3, 5)
    assert game.attempt_place((0, 0), 3, 5) is True

    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2
    assert game.wildcard_index is None
    assert game.wildcard_original_roll is None


def test_reroll_disabled_by_default():
    game = Game(rng=ScriptedRandom([4, 6]))
    game.roll_dice()
    assert game.can_reroll() is False


def test_reroll_from_choosing_placement_gets_a_fresh_roll():
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([2, 3, 4, 5]))
    game.roll_dice()
    assert game.last_roll == (2, 3)
    p1 = game.players[PLAYER_1]
    assert game.can_reroll() is True

    game.reroll()
    assert p1.rerolls_used == 1
    assert game.last_roll == (4, 5)
    assert game.state == TurnState.CHOOSING_PLACEMENT


def test_reroll_charges_are_capped_and_raise_once_exhausted():
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([2, 3] * (REROLL_LIMIT + 1)))
    game.roll_dice()
    for _ in range(REROLL_LIMIT):
        game.reroll()
    p1 = game.players[PLAYER_1]
    assert p1.rerolls_used == REROLL_LIMIT
    assert game.can_reroll() is False
    with pytest.raises(ValueError):
        game.reroll()


def test_reroll_raises_outside_a_pending_roll():
    game = Game(board_size=6, reroll_enabled=True)
    with pytest.raises(ValueError):
        game.reroll()  # AWAITING_ROLL - nothing to discard


def test_skip_commit_is_deferred_while_a_reroll_charge_is_available():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    p1 = game.players[PLAYER_1]
    assert p1.consecutive_skips == 0  # not committed yet
    assert game.history == []


def test_confirm_skip_commits_a_deferred_skip():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    p1 = game.players[PLAYER_1]

    game.confirm_skip()
    assert p1.consecutive_skips == 1
    assert len(game.history) == 1
    assert game.history[0].placed is None


def test_confirm_skip_is_a_noop_when_already_committed():
    # reroll disabled -> _resolve_roll() commits immediately, same as today;
    # confirm_skip() must not double-count it.
    game = Game(board_size=2, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    p1 = game.players[PLAYER_1]
    assert p1.consecutive_skips == 1

    game.confirm_skip()
    assert p1.consecutive_skips == 1
    assert len(game.history) == 1


def test_reroll_from_skipped_never_commits_the_discarded_skip():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6, 1, 1]))
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    p1 = game.players[PLAYER_1]

    game.reroll()
    assert p1.rerolls_used == 1
    assert p1.consecutive_skips == 0  # the discarded skip was never recorded
    assert game.history == []
    assert game.last_roll == (1, 1)


def test_reroll_from_choosing_wildcard_discards_the_pending_wildcard():
    game = Game(board_size=6, wildcard_enabled=True, reroll_enabled=True, rng=ScriptedRandom([3, 3, 0, 4, 5]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    game.reroll()
    assert game.last_roll == (4, 5)
    assert game.wildcard_index is None
    assert game.wildcard_original_roll is None
    assert game.state == TurnState.CHOOSING_PLACEMENT


def test_choose_wildcard_value_raises_when_not_choosing_wildcard():
    game = Game(rng=ScriptedRandom([4, 6]))
    game.roll_dice()
    with pytest.raises(ValueError):
        game.choose_wildcard_value(3)


@pytest.mark.parametrize("value", [0, 7])
def test_choose_wildcard_value_raises_for_out_of_range_value(value):
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([3, 3, 0]))
    game.roll_dice()
    with pytest.raises(ValueError):
        game.choose_wildcard_value(value)


def test_self_enclosed_penalty_disabled_by_default_score_equals_area():
    game = Game(board_size=6)
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=2, h=2)
    assert game.total_score(p1) == p1.total_area == 4


def test_self_enclosed_penalty_docks_points_for_a_self_enclosed_hole():
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (1, 2), w=1, h=1)
    game.board.place(p1, (3, 2), w=1, h=1)
    game.board.place(p1, (2, 1), w=1, h=1)
    game.board.place(p1, (2, 3), w=1, h=1)
    game.board.place(p2, (5, 5), w=1, h=1)

    assert p1.total_area == 4
    assert game.total_score(p1) == 4 - SELF_ENCLOSED_PENALTY_PER_CELL  # one enclosed cell at (2, 2)
    assert game.total_score(p2) == p2.total_area  # p2's own area is untouched


def test_self_enclosed_penalty_drops_once_the_hole_is_filled():
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (1, 2), w=1, h=1)
    game.board.place(p1, (3, 2), w=1, h=1)
    game.board.place(p1, (2, 1), w=1, h=1)
    game.board.place(p1, (2, 3), w=1, h=1)
    game.board.place(p2, (5, 5), w=1, h=1)
    assert game.total_score(p1) == p1.total_area - SELF_ENCLOSED_PENALTY_PER_CELL

    game.board.place(p1, (2, 2), w=1, h=1)
    assert game.total_score(p1) == p1.total_area  # hole filled - live penalty drops immediately
