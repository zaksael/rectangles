import pytest

from rectangles.constants import PLAYER_1, PLAYER_2
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


def test_doubles_grants_bonus_turn_after_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True

    if not game.check_game_over():
        game.end_turn()

    assert game.current_player_id == PLAYER_1
    assert game.state == TurnState.AWAITING_ROLL


def test_repeated_double_skips_still_reach_skip_limit_without_alternating():
    game = Game(board_size=4, skip_limit=2, rng=ScriptedRandom([6, 6, 6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty; a 6x6 never fits

    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert p1.consecutive_skips == 1
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_1  # doubles: bonus turn even on a skip

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
    # Every roll here is a double (1,1), which is unavoidable to script literal
    # 1x1 placements on a 2x2 board - so under the doubles-bonus-turn rule,
    # p1 keeps its turn throughout and claims all four cells itself.
    game = Game(board_size=2, rng=ScriptedRandom([1, 1, 1, 1, 1, 1, 1, 1]))

    game.roll_dice()
    assert game.attempt_place((0, 0), 1, 1) is True  # p1 anchors at (0,0)
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_1  # doubles: bonus turn

    game.roll_dice()
    assert game.attempt_place((0, 1), 1, 1) is True  # p1 claims (0,1)
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_1

    game.roll_dice()
    assert game.attempt_place((1, 0), 1, 1) is True  # p1 claims (1,0)
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_1

    game.roll_dice()
    assert game.attempt_place((1, 1), 1, 1) is True  # p1 claims the last cell
    assert game.check_game_over() is True
    assert game.state == TurnState.GAME_OVER


def test_board_full_reports_board_full_reason():
    # See test_game_over_detection_after_placement for why every roll is a
    # double here.
    game = Game(board_size=2, rng=ScriptedRandom([1, 1, 1, 1, 1, 1, 1, 1]))
    game.roll_dice()
    game.attempt_place((0, 0), 1, 1)
    game.end_turn()
    game.roll_dice()
    game.attempt_place((0, 1), 1, 1)
    game.end_turn()
    game.roll_dice()
    game.attempt_place((1, 0), 1, 1)
    game.end_turn()
    game.roll_dice()
    game.attempt_place((1, 1), 1, 1)

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
    # None of these rolls are doubles, so turns alternate normally - p2's
    # own start corner (its only possible anchor, since it hasn't moved) is
    # pre-occupied so every one of its rolls is an unconditional skip
    # regardless of dice value.
    game = Game(board_size=4, skip_limit=2, rng=ScriptedRandom([1, 2, 3, 5, 2, 1, 1, 3]))
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (3, 3), w=1, h=1)

    # Turn 1: p1 rolls (1,2) and places adjacent to its own (3,3) cell.
    game.roll_dice()
    assert game.attempt_place((1, 3), 1, 2) is True
    assert game.check_game_over() is False
    game.end_turn()
    assert game.current_player_id == PLAYER_2  # not doubles: turn alternates

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
