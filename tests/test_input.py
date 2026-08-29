import pygame

from rectangles import persistence
from rectangles.constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    PLAYER_1,
    PLAYER_2,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
    TOURNAMENT_SIZE_PRESETS,
)
from rectangles.game import Game, TurnState
from rectangles.series import Series
from rectangles.tournament import Bracket, Participant
from rectangles.ui import layout
from rectangles.ui.input import (
    apply_match_identity,
    build_tournament_participants,
    compute_top_left,
    handle_event,
    handle_mode_select_event,
    handle_replay_event,
    handle_settings_event,
    handle_tournament_event,
    take_bot_turn,
    update_hover,
)
from rectangles.ui.state import ConfirmAction, Screen, UIState


class ScriptedRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def _finished_game(board_size, p1_area, p2_area):
    game = Game(board_size=board_size)
    if p1_area:
        game.board.place(game.players[PLAYER_1], (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(game.players[PLAYER_2], (0, 0), p2_area, 1)
    return game


def test_compute_top_left_centers_small_piece_on_cell():
    game = Game(board_size=6)
    # A 2x2 piece centered on (2, 3): offset back by w//2=1, h//2=1.
    assert compute_top_left(game, w=2, h=2, cell=(2, 3)) == (1, 2)


def test_compute_top_left_clamps_upper_bound():
    game = Game(board_size=6)
    # A 3x3 piece centered on (5, 5) would overrun the board; clamp to fit.
    assert compute_top_left(game, w=3, h=3, cell=(5, 5)) == (3, 3)


def test_compute_top_left_clamps_lower_bound():
    game = Game(board_size=6)
    # A 3x3 piece centered on (0, 0) would go negative; clamp to fit.
    assert compute_top_left(game, w=3, h=3, cell=(0, 0)) == (0, 0)


def test_compute_top_left_same_for_both_players():
    game = Game(board_size=6)
    p1_result = compute_top_left(game, w=2, h=2, cell=(3, 3))
    game.current_player_id = PLAYER_2
    p2_result = compute_top_left(game, w=2, h=2, cell=(3, 3))
    assert p1_result == p2_result == (2, 2)


def test_compute_top_left_centers_odd_dimension_piece():
    game = Game(board_size=6)
    # A 3x3 piece has an exact center cell; (3, 3) centers with no clamping.
    assert compute_top_left(game, w=3, h=3, cell=(3, 3)) == (2, 2)


def _played_game() -> Game:
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    game.attempt_place((0, 0), 2, 2)
    return game


def test_new_game_key_without_history_resets_immediately():
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.MODE_SELECT


def test_new_game_key_with_history_requests_confirmation():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation == ConfirmAction.NEW_GAME
    assert ui_state.screen == Screen.PLAYING


def test_confirm_new_game_with_enter_performs_reset():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.MODE_SELECT


def test_cancel_new_game_with_escape_leaves_state_untouched():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.PLAYING
    assert len(game.history) == 1


def test_quit_mid_match_with_history_requests_confirmation():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.QUIT)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation == ConfirmAction.EXIT


def test_quit_without_history_returns_false_immediately():
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.QUIT)

    assert handle_event(event, game, ui_state) is False
    assert ui_state.pending_confirmation is None


def test_quit_after_game_over_returns_false_immediately():
    game = _played_game()
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.QUIT)

    assert handle_event(event, game, ui_state) is False
    assert ui_state.pending_confirmation is None


def test_confirm_exit_with_enter_returns_false():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.EXIT)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

    assert handle_event(event, game, ui_state) is False


def test_surrender_key_always_requests_confirmation():
    # Unlike New Game/Exit, surrender asks for confirmation even with no history.
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation == ConfirmAction.SURRENDER
    assert game.state != TurnState.GAME_OVER


def test_confirm_surrender_with_enter_ends_game():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.SURRENDER)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert game.state == TurnState.GAME_OVER
    assert game.surrendered_player_id == game.current_player_id


def test_cancel_surrender_with_escape_leaves_game_untouched():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.SURRENDER)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert game.state != TurnState.GAME_OVER


def test_mousewheel_scrolls_history_only_over_history_region(monkeypatch):
    game = Game(board_size=6)
    game.history = [None] * 12  # length is all that matters for clamping
    ui_state = UIState(screen=Screen.PLAYING)
    inside = layout.PANEL_HISTORY_REGION_RECT.center
    event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)

    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: inside)
    handle_event(event, game, ui_state)
    assert ui_state.history_scroll == 1

    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (0, 0))
    handle_event(event, game, ui_state)
    assert ui_state.history_scroll == 1  # outside the region: unchanged


def test_mousewheel_scroll_clamps_at_bounds(monkeypatch):
    game = Game(board_size=6)
    game.history = [None] * 12
    ui_state = UIState(screen=Screen.PLAYING, history_scroll=100)
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: layout.PANEL_HISTORY_REGION_RECT.center)

    handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1), game, ui_state)
    max_offset = len(game.history) - layout.PANEL_HISTORY_MAX_ROWS
    assert ui_state.history_scroll == max_offset

    ui_state.history_scroll = 0
    handle_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), game, ui_state)
    assert ui_state.history_scroll == 0


# --- Rolling and placing ------------------------------------------------


def test_roll_dice_key_sets_current_dims_to_rolled_order_when_legal():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)

    assert handle_event(event, game, ui_state) is True

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert ui_state.current_dims == (2, 3)


def test_roll_button_click_rolls_dice():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.ROLL_BUTTON_RECT.center)

    assert handle_event(event, game, ui_state) is True

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert ui_state.current_dims == (2, 3)


def test_left_click_on_legal_cell_places_piece_and_advances_turn():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d), game, ui_state)
    pos = layout.cell_rect(0, 0, board_size=6).center  # P1's start corner - anchors the first piece

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    assert handle_event(event, game, ui_state) is True

    assert [(r.top_left, r.width, r.height) for r in game.players[PLAYER_1].pieces] == [((0, 0), 2, 3)]
    assert game.state == TurnState.AWAITING_ROLL  # non-double roll: turn ended
    assert game.current_player_id == PLAYER_2
    assert ui_state.current_dims is None  # ui_state.reset() after a successful placement


def test_left_click_on_illegal_cell_does_not_place():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d), game, ui_state)
    pos = layout.cell_rect(5, 5, board_size=6).center  # far from P1's start corner - not anchored, illegal

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    assert handle_event(event, game, ui_state) is True

    assert game.players[PLAYER_1].pieces == []
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert ui_state.current_dims == (2, 3)  # untouched - no reset on a failed placement


def test_rotate_key_swaps_dims_during_choosing_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d), game, ui_state)

    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r), game, ui_state)

    assert ui_state.current_dims == (3, 2)


def test_rotate_button_click_swaps_dims():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d), game, ui_state)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.ROTATE_BUTTON_RECT.center)
    handle_event(event, game, ui_state)

    assert ui_state.current_dims == (3, 2)


def test_right_click_rotates_during_choosing_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState(screen=Screen.PLAYING)
    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d), game, ui_state)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(0, 0))
    handle_event(event, game, ui_state)

    assert ui_state.current_dims == (3, 2)


def _skipped_game() -> Game:
    # Only (3, 3) remains empty; a rolled 6x6 has nowhere to go, so the turn
    # is skipped.
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    return game


def test_continue_key_space_on_skipped_ends_turn():
    game = _skipped_game()
    ui_state = UIState(screen=Screen.PLAYING)

    handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE), game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert game.current_player_id == PLAYER_2


def test_continue_button_click_on_skipped_ends_turn():
    game = _skipped_game()
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.CONTINUE_BUTTON_RECT.center)
    handle_event(event, game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert game.current_player_id == PLAYER_2


def test_take_bot_turn_rolls_when_awaiting_roll():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState()
    assert game.state == TurnState.AWAITING_ROLL

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.last_roll == (2, 3)


def test_take_bot_turn_continues_when_skipped():
    game = _skipped_game()
    ui_state = UIState(active_bot_seats={PLAYER_1: "Basic"})

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL


def test_take_bot_turn_places_when_choosing_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3, 0]))
    ui_state = UIState(active_bot_seats={PLAYER_1: "Basic"})
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert len(game.players[PLAYER_1].pieces) == 1


def test_wildcard_value_button_click_finalizes_choice_and_advances_state():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([5, 5, 0]))
    ui_state = UIState(screen=Screen.PLAYING)
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.WILDCARD_VALUE_BUTTON_RECTS[6].center
    )
    handle_event(event, game, ui_state)

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.last_roll == (6, 5)
    assert ui_state.current_dims == (6, 5)


def test_reroll_click_in_choosing_placement_gets_a_fresh_roll():
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([2, 3, 4, 5]))
    ui_state = UIState(screen=Screen.PLAYING)
    game.roll_dice()
    ui_state.current_dims = (2, 3)
    assert game.state == TurnState.CHOOSING_PLACEMENT

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.REROLL_PLACEMENT_BUTTON_RECT.center
    )
    handle_event(event, game, ui_state)

    assert game.players[PLAYER_1].rerolls_used == 1
    assert game.last_roll == (4, 5)
    assert ui_state.current_dims == (4, 5)


def test_reroll_click_in_choosing_wildcard_discards_the_pending_wildcard():
    game = Game(
        board_size=6, wildcard_enabled=True, reroll_enabled=True, rng=ScriptedRandom([3, 3, 0, 4, 5])
    )
    ui_state = UIState(screen=Screen.PLAYING)
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.REROLL_WILDCARD_BUTTON_RECT.center
    )
    handle_event(event, game, ui_state)

    assert game.players[PLAYER_1].rerolls_used == 1
    assert game.last_roll == (4, 5)
    assert game.wildcard_original_roll is None


def test_reroll_click_in_skipped_never_commits_the_discarded_skip():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6, 1, 1]))
    ui_state = UIState(screen=Screen.PLAYING)
    game.roll_dice()
    assert game.state == TurnState.SKIPPED

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.REROLL_SKIPPED_BUTTON_RECT.center
    )
    handle_event(event, game, ui_state)

    p1 = game.players[PLAYER_1]
    assert p1.rerolls_used == 1
    assert p1.consecutive_skips == 0
    assert game.history == []
    assert game.last_roll == (1, 1)


def test_skip_button_click_in_skipped_commits_the_skip():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6]))
    ui_state = UIState(screen=Screen.PLAYING)
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    p1 = game.players[PLAYER_1]
    assert p1.consecutive_skips == 0

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SKIP_BUTTON_RECT.center)
    handle_event(event, game, ui_state)

    assert p1.consecutive_skips == 1
    assert len(game.history) == 1


def test_take_bot_turn_basic_never_uses_reroll_even_when_available():
    # Basic always accepts whatever it rolls/skips - reroll charges (like
    # Wildcard Roll's value pick) stay dumb for Basic. Greedy/Blocking do use
    # both now - see the should_reroll-driven tests below.
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6]))
    ui_state = UIState()
    game.current_player_id = PLAYER_2
    ui_state.active_bot_seats = {PLAYER_2: "Basic"}
    game.roll_dice()
    assert game.state == TurnState.SKIPPED

    take_bot_turn(game, ui_state)

    p2 = game.players[PLAYER_2]
    assert p2.rerolls_used == 0
    assert p2.consecutive_skips == 1


def test_take_bot_turn_blocking_rerolls_from_choosing_placement_at_zero_score():
    # Blocking, not Greedy: Greedy's flag_score is structurally 0 without
    # Flag Conquest on (rectangles/bot.py's should_reroll guard), so it
    # wouldn't reroll here at all - see test_bot.py's coverage of that guard.
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([1, 1, 2, 3]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()
    ui_state = UIState(active_bot_seats={PLAYER_1: "Blocking"})
    assert game.state == TurnState.CHOOSING_PLACEMENT

    take_bot_turn(game, ui_state)

    p1 = game.players[PLAYER_1]
    assert p1.rerolls_used == 1
    assert len(p1.pieces) == 1  # the discarded roll was never placed
    assert game.last_roll == (2, 3)


def test_take_bot_turn_greedy_rerolls_from_skipped():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6, 1, 1]))
    ui_state = UIState(active_bot_seats={PLAYER_1: "Greedy"})
    game.roll_dice()
    assert game.state == TurnState.SKIPPED

    take_bot_turn(game, ui_state)

    p1 = game.players[PLAYER_1]
    assert p1.rerolls_used == 1
    assert p1.consecutive_skips == 0  # the discarded skip was never committed
    assert game.last_roll == (1, 1)


def test_take_bot_turn_blocking_rerolls_from_choosing_wildcard_at_zero_score():
    # Blocking, not Greedy - see the comment on the CHOOSING_PLACEMENT variant above.
    game = Game(
        board_size=6, wildcard_enabled=True, reroll_enabled=True, rng=ScriptedRandom([5, 5, 0, 2, 3])
    )
    ui_state = UIState(active_bot_seats={PLAYER_1: "Blocking"})
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    take_bot_turn(game, ui_state)

    assert game.players[PLAYER_1].rerolls_used == 1
    assert game.last_roll == (2, 3)


def test_take_bot_turn_greedy_picks_the_flag_capturing_wildcard_value():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([2, 2, 0]))
    game.board.place(game.players[PLAYER_1], (2, 2), 1, 1)
    game.board.flag_cells = frozenset({(2, 5)})
    ui_state = UIState(active_bot_seats={PLAYER_1: "Greedy"})
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.last_roll == (3, 2)


def test_take_bot_turn_resolves_choosing_wildcard():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([5, 5, 0, 6]))
    ui_state = UIState(active_bot_seats={PLAYER_1: "Basic"})
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.last_roll == (6, 5)
    assert ui_state.current_dims == (6, 5)


def test_human_roll_click_ignored_during_bots_turn():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.current_player_id = PLAYER_2
    ui_state = UIState(screen=Screen.PLAYING, active_bot_seats={PLAYER_2: "Basic"})

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.ROLL_BUTTON_RECT.center)
    handle_event(event, game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert game.last_roll is None


def test_update_hover_sets_top_left_and_legal_flag(monkeypatch):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    ui_state = UIState(screen=Screen.PLAYING, current_dims=(2, 3))
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: layout.cell_rect(0, 0, board_size=6).center)

    update_hover(game, ui_state)

    assert ui_state.hover_top_left == (0, 0)
    assert ui_state.hover_legal is True


def test_update_hover_clears_outside_choosing_placement():
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING, hover_top_left=(1, 1))

    update_hover(game, ui_state)

    assert ui_state.hover_top_left is None


# --- Game-over navigation, with and without a series --------------------


def test_game_over_new_game_button_without_series_returns_to_mode_select():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_NEW_GAME_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state, series=None) is True

    assert ui_state.screen == Screen.MODE_SELECT


def test_game_over_new_game_button_with_incomplete_series_requests_next_game():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))  # 1 of 3 rounds played, not yet decided
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_NEW_GAME_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state, series) is True

    assert ui_state.next_game_requested is True
    assert ui_state.screen == Screen.PLAYING  # app.py builds the next round; no screen change here


def test_game_over_new_game_button_with_completed_series_returns_to_mode_select():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))  # all 3 rounds played
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_NEW_GAME_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state, series) is True

    assert ui_state.next_game_requested is False
    assert ui_state.screen == Screen.MODE_SELECT


def test_game_over_key_n_with_incomplete_series_requests_next_game():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
    assert handle_event(event, game, ui_state, series) is True

    assert ui_state.next_game_requested is True


def test_game_over_new_game_button_with_decided_series_and_tournament_requests_next_match():
    from rectangles.tournament import Bracket, Participant

    tournament = Bracket(
        participants=[Participant(name=f"Player {i + 1}") for i in range(4)],
        series_length=3,
        board_size=6,
        skip_limit=3,
    )
    match = tournament.current_match()
    series = tournament.new_series_for_current_match()
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))  # decided, not tied
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_NEW_GAME_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state, series, tournament) is True

    assert ui_state.next_match_requested is True
    assert ui_state.screen == Screen.PLAYING  # app.py resolves the transition; no screen change here


def test_game_over_bracket_button_click_enters_tournament_screen():
    from rectangles.tournament import Bracket, Participant

    tournament = Bracket(
        participants=[Participant(name=f"Player {i + 1}") for i in range(4)],
        series_length=3,
        board_size=6,
        skip_limit=3,
    )
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_BRACKET_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state, None, tournament) is True

    assert ui_state.screen == Screen.TOURNAMENT


def test_game_over_exit_button_click_returns_false():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_EXIT_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state) is False


def test_game_over_escape_key_returns_false():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert handle_event(event, game, ui_state) is False


# --- Replay screen --------------------------------------------------------


def test_game_over_replay_button_click_enters_replay_screen():
    game = _played_game()
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        button=1,
        pos=layout.GAME_OVER_REPLAY_BUTTON_RECT.center,
    )
    assert handle_event(event, game, ui_state, series=None) is True

    assert ui_state.screen == Screen.REPLAY
    assert ui_state.replay_step == 0


def test_replay_first_prev_next_last_button_navigation():
    game = _played_game()  # one history entry: step ranges over [0, 1]
    ui_state = UIState(screen=Screen.REPLAY, replay_step=1)
    rects = layout.REPLAY_BUTTON_RECTS

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["prev"].center)
    assert handle_replay_event(event, ui_state, game) is True
    assert ui_state.replay_step == 0

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["next"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_step == 1

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["first"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_step == 0

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["last"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_step == 1


def test_replay_first_and_last_buttons_jump_across_multiple_steps():
    # A single history entry can't distinguish "First"/"Last" (jump straight
    # to the boundary) from "Prev"/"Next" (step by one) - both land on the
    # same result. Three turns make the distinction provable: from the last
    # step, a single Prev would only reach step 2, but First must reach 0.
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3, 1, 2]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((0, 2), 1, 2) is True
    assert len(game.history) == 3

    rects = layout.REPLAY_BUTTON_RECTS

    ui_state = UIState(screen=Screen.REPLAY, replay_step=3)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["first"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_step == 0

    ui_state = UIState(screen=Screen.REPLAY, replay_step=0)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["last"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_step == 3


def test_replay_arrow_and_home_end_keys_step():
    game = _played_game()
    ui_state = UIState(screen=Screen.REPLAY, replay_step=1)

    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), ui_state, game)
    assert ui_state.replay_step == 0

    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT), ui_state, game)
    assert ui_state.replay_step == 1

    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME), ui_state, game)
    assert ui_state.replay_step == 0

    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END), ui_state, game)
    assert ui_state.replay_step == 1


def test_replay_step_clamps_at_bounds():
    game = _played_game()
    ui_state = UIState(screen=Screen.REPLAY, replay_step=0)

    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LEFT), ui_state, game)
    assert ui_state.replay_step == 0

    ui_state.replay_step = len(game.history)
    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT), ui_state, game)
    assert ui_state.replay_step == len(game.history)


def test_replay_escape_and_back_button_return_to_playing():
    game = _played_game()

    ui_state = UIState(screen=Screen.REPLAY, replay_step=1)
    handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), ui_state, game)
    assert ui_state.screen == Screen.PLAYING

    ui_state = UIState(screen=Screen.REPLAY, replay_step=1)
    rects = layout.REPLAY_BUTTON_RECTS
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["back"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.screen == Screen.PLAYING


def test_replay_quit_event_returns_false():
    game = _played_game()
    ui_state = UIState(screen=Screen.REPLAY, replay_step=1)

    event = pygame.event.Event(pygame.QUIT)
    assert handle_replay_event(event, ui_state, game) is False


def test_game_over_replay_button_click_resets_autoplay():
    game = _played_game()
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING, replay_autoplay=True)

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_REPLAY_BUTTON_RECT.center
    )
    handle_event(event, game, ui_state, series=None)

    assert ui_state.replay_autoplay is False


def test_replay_play_button_toggles_autoplay():
    game = _played_game()
    ui_state = UIState(screen=Screen.REPLAY, replay_step=0)
    rects = layout.REPLAY_BUTTON_RECTS

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["play"].center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_autoplay is True

    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_autoplay is False


def test_replay_speed_button_sets_speed_without_touching_autoplay():
    game = _played_game()
    ui_state = UIState(screen=Screen.REPLAY, replay_step=0, replay_autoplay=True)
    rects = layout.REPLAY_BUTTON_RECTS

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["Fast"].center)
    handle_replay_event(event, ui_state, game)

    assert ui_state.replay_speed == "Fast"
    assert ui_state.replay_autoplay is True


def test_replay_reveal_button_toggles_without_touching_autoplay():
    game = _played_game()
    ui_state = UIState(screen=Screen.REPLAY, replay_step=0, replay_autoplay=True)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.REPLAY_REVEAL_BUTTON_RECT.center)
    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_show_better_option is True
    assert ui_state.replay_autoplay is True

    handle_replay_event(event, ui_state, game)
    assert ui_state.replay_show_better_option is False


def test_replay_manual_nav_buttons_pause_autoplay():
    game = _played_game()
    rects = layout.REPLAY_BUTTON_RECTS
    for key in ("first", "prev", "next", "last"):
        ui_state = UIState(screen=Screen.REPLAY, replay_step=1, replay_autoplay=True)
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects[key].center)
        handle_replay_event(event, ui_state, game)
        assert ui_state.replay_autoplay is False, key


def test_replay_manual_nav_keys_pause_autoplay():
    game = _played_game()
    for key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_HOME, pygame.K_END):
        ui_state = UIState(screen=Screen.REPLAY, replay_step=1, replay_autoplay=True)
        handle_replay_event(pygame.event.Event(pygame.KEYDOWN, key=key), ui_state, game)
        assert ui_state.replay_autoplay is False, key


# --- Confirmation dialog, mouse path -------------------------------------


def test_confirm_yes_button_click_performs_new_game():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.CONFIRM_YES_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.MODE_SELECT


def test_confirm_no_button_click_cancels():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.CONFIRM_NO_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.PLAYING


# --- Settings screen ------------------------------------------------------


def test_settings_quit_event_returns_false():
    assert handle_settings_event(pygame.event.Event(pygame.QUIT), UIState()) is False


def test_settings_escape_key_returns_to_mode_select():
    ui_state = UIState()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.screen == Screen.MODE_SELECT


def test_settings_space_key_starts_game(monkeypatch):
    monkeypatch.setattr(persistence, "delete_save", lambda: None)
    ui_state = UIState()

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.game_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_mode_select_r_key_resumes_only_when_a_save_exists(monkeypatch):
    ui_state = UIState()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)

    monkeypatch.setattr(persistence, "has_save", lambda: False)
    handle_mode_select_event(event, ui_state)
    assert ui_state.resume_requested is False

    monkeypatch.setattr(persistence, "has_save", lambda: True)
    handle_mode_select_event(event, ui_state)
    assert ui_state.resume_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_settings_board_size_buttons_update_selection():
    ui_state = UIState()
    for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.selected_board_size == value
    assert set(layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS) == set(BOARD_SIZE_PRESETS)


def test_settings_skip_limit_buttons_update_selection():
    ui_state = UIState()
    for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.selected_skip_limit == value
    assert set(layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS) == set(SKIP_LIMIT_PRESETS)


def test_settings_flag_conquest_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_flag_conquest_enabled is False

    rect = layout.settings_house_rule_button_rects("Single", ui_state.tournament_size)["Flags"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_flag_conquest_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_flag_conquest_enabled is False


def test_settings_walls_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_walls_enabled is False

    rect = layout.settings_house_rule_button_rects("Single", ui_state.tournament_size)["Walls"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_walls_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_walls_enabled is False


def test_settings_wildcard_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_wildcard_enabled is False

    rect = layout.settings_house_rule_button_rects("Single", ui_state.tournament_size)["Wildcard"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_wildcard_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_wildcard_enabled is False


def test_settings_self_enclosed_penalty_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_self_enclosed_penalty_enabled is False

    rect = layout.settings_house_rule_button_rects("Single", ui_state.tournament_size)["Enclosure"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_self_enclosed_penalty_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_self_enclosed_penalty_enabled is False


def test_settings_reroll_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_reroll_enabled is False

    rect = layout.settings_house_rule_button_rects("Single", ui_state.tournament_size)["Reroll"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_reroll_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_reroll_enabled is False


def test_settings_all_rules_button_turns_all_on_then_all_off():
    ui_state = UIState()
    assert ui_state.all_house_rules_enabled is False

    rect = layout.settings_all_rules_button_rect("Single", ui_state.tournament_size)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_flag_conquest_enabled is True
    assert ui_state.selected_walls_enabled is True
    assert ui_state.selected_obstacles_enabled is True
    assert ui_state.selected_wildcard_enabled is True
    assert ui_state.selected_self_enclosed_penalty_enabled is True
    assert ui_state.selected_reroll_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_flag_conquest_enabled is False
    assert ui_state.selected_walls_enabled is False
    assert ui_state.selected_obstacles_enabled is False
    assert ui_state.selected_wildcard_enabled is False
    assert ui_state.selected_self_enclosed_penalty_enabled is False
    assert ui_state.selected_reroll_enabled is False


def test_settings_all_rules_button_turns_all_on_from_a_mixed_state():
    ui_state = UIState(selected_flag_conquest_enabled=True, selected_walls_enabled=False)

    rect = layout.settings_all_rules_button_rect("Single", ui_state.tournament_size)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.all_house_rules_enabled is True


def test_settings_opponent_buttons_update_selection():
    # One unified 4-way row (Human + 3 bot difficulties) replaces the old
    # separate vs-Bot toggle and Bot-difficulty rows.
    ui_state = UIState(selected_game_mode="Single")
    rects = layout.settings_opponent_button_rects("Single", ui_state.tournament_size)
    assert set(rects) == {"Human"} | set(BOT_DIFFICULTY_PRESETS)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["Greedy"].center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_bot_enabled is True
    assert ui_state.selected_bot_difficulty == "Greedy"

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rects["Human"].center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_bot_enabled is False


def test_settings_series_length_buttons_update_selection():
    ui_state = UIState(selected_game_mode="Series")
    for value, rect in layout.settings_series_length_button_rects("Series", ui_state.tournament_size).items():
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.selected_series_length == value
    assert set(layout.settings_series_length_button_rects("Series", ui_state.tournament_size)) == set(SERIES_LENGTH_PRESETS)


def test_settings_start_game_button_click_deletes_save_and_starts(monkeypatch):
    deleted = []
    monkeypatch.setattr(persistence, "delete_save", lambda: deleted.append(True))
    ui_state = UIState(selected_game_mode="Single")

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.settings_start_button_rect("Single", ui_state.tournament_size).center
    )
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.game_requested is True
    assert ui_state.screen == Screen.PLAYING
    assert deleted == [True]


def test_settings_start_series_button_click_starts_series(monkeypatch):
    monkeypatch.setattr(persistence, "delete_save", lambda: None)
    ui_state = UIState(selected_game_mode="Series")

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.settings_start_button_rect("Series", ui_state.tournament_size).center
    )
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.series_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_settings_start_tournament_button_click_starts_tournament(monkeypatch):
    monkeypatch.setattr(persistence, "delete_save", lambda: None)
    ui_state = UIState(selected_game_mode="Tournament")

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN,
        button=1,
        pos=layout.settings_start_button_rect("Tournament", ui_state.tournament_size).center,
    )
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.tournament_requested is True
    assert ui_state.screen == Screen.TOURNAMENT


def test_settings_back_button_click_returns_to_mode_select():
    ui_state = UIState()
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.settings_back_button_rect("Single", ui_state.tournament_size).center
    )
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.screen == Screen.MODE_SELECT


def test_mode_select_resume_button_click_only_when_a_save_exists(monkeypatch):
    ui_state = UIState()
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.MODE_SELECT_RESUME_BUTTON_RECT.center
    )

    monkeypatch.setattr(persistence, "has_save", lambda: False)
    handle_mode_select_event(event, ui_state)
    assert ui_state.resume_requested is False

    monkeypatch.setattr(persistence, "has_save", lambda: True)
    handle_mode_select_event(event, ui_state)
    assert ui_state.resume_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_settings_exit_button_click_returns_false():
    ui_state = UIState()
    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.settings_exit_button_rect("Single", ui_state.tournament_size).center
    )
    assert handle_settings_event(event, ui_state) is False


def test_mode_select_exit_button_click_returns_false():
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.MODE_SELECT_EXIT_BUTTON_RECT.center)
    assert handle_mode_select_event(event, UIState()) is False


def test_mode_select_button_click_selects_mode_and_enters_settings():
    for mode, rect in layout.MODE_SELECT_BUTTON_RECTS.items():
        ui_state = UIState()
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_mode_select_event(event, ui_state) is True
        assert ui_state.selected_game_mode == mode
        assert ui_state.screen == Screen.SETTINGS


def test_mode_select_button_click_resets_stale_settings_scroll():
    ui_state = UIState(settings_scroll=500)
    rect = layout.MODE_SELECT_BUTTON_RECTS["Tournament"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
    handle_mode_select_event(event, ui_state)
    assert ui_state.settings_scroll == 0


def test_settings_mousewheel_scrolls_and_clamps(monkeypatch):
    # settings_max_scroll() is 0 at today's content height for Single/Series
    # (the whole card stack already fits within DESIGN_HEIGHT - see
    # layout.py) - fake real scroll headroom directly rather than via window
    # size, since the real window no longer affects how much design-space
    # content fits at all (see layout.compute_scale/DESIGN_HEIGHT).
    max_scroll = 200
    monkeypatch.setattr(layout, "settings_max_scroll", lambda mode, tournament_size: max_scroll)

    ui_state = UIState()

    handle_settings_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), ui_state)
    assert ui_state.settings_scroll == 40

    ui_state.settings_scroll = max_scroll
    handle_settings_event(pygame.event.Event(pygame.MOUSEWHEEL, y=-1), ui_state)
    assert ui_state.settings_scroll == max_scroll  # clamped at max

    ui_state.settings_scroll = 0
    handle_settings_event(pygame.event.Event(pygame.MOUSEWHEEL, y=1), ui_state)
    assert ui_state.settings_scroll == 0  # clamped at 0


def test_settings_click_position_accounts_for_scroll_offset():
    ui_state = UIState(settings_scroll=50)
    # The button visually sits 50px higher on screen than its content-space rect.
    rect = layout.settings_house_rule_button_rects("Single", ui_state.tournament_size)["Walls"]
    screen_pos = (rect.centerx, rect.centery - 50)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen_pos)

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_walls_enabled is True


# --- Tournament -------------------------------------------------------------


def test_settings_tournament_size_buttons_update_selection():
    ui_state = UIState(selected_game_mode="Tournament")
    for value, rect in layout.settings_tournament_size_button_rects(ui_state.tournament_size).items():
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.tournament_size == value
    assert set(layout.settings_tournament_size_button_rects(ui_state.tournament_size)) == set(TOURNAMENT_SIZE_PRESETS)


def test_settings_tournament_size_click_clamps_scroll_when_shrinking():
    ui_state = UIState(selected_game_mode="Tournament", tournament_size=8)
    ui_state.settings_scroll = layout.settings_max_scroll("Tournament", 8)
    small_size = min(TOURNAMENT_SIZE_PRESETS)

    rect = layout.settings_tournament_size_button_rects(8)[small_size]
    screen_pos = (rect.centerx, rect.centery - ui_state.settings_scroll)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=screen_pos)
    handle_settings_event(event, ui_state)

    assert ui_state.tournament_size == small_size
    assert ui_state.settings_scroll <= layout.settings_max_scroll("Tournament", small_size)


def test_settings_tournament_slot_toggle_switches_human_to_bot():
    ui_state = UIState(selected_game_mode="Tournament")
    rect = layout.settings_tournament_slot_toggle_rect(ui_state.tournament_size, 0)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.tournament_slot_is_bot[0] is True

    handle_settings_event(event, ui_state)
    assert ui_state.tournament_slot_is_bot[0] is False


def test_settings_tournament_slot_difficulty_only_updates_when_slot_is_bot():
    ui_state = UIState(selected_game_mode="Tournament")
    rect = layout.settings_tournament_slot_difficulty_rects(ui_state.tournament_size, 0)["Greedy"]
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)

    handle_settings_event(event, ui_state)
    assert ui_state.tournament_slot_difficulty[0] == BOT_DIFFICULTY_PRESETS[0]  # ignored - slot 0 is Human

    ui_state.tournament_slot_is_bot[0] = True
    handle_settings_event(event, ui_state)
    assert ui_state.tournament_slot_difficulty[0] == "Greedy"


def test_settings_tournament_slot_click_ignores_rows_past_the_selected_size():
    ui_state = UIState(selected_game_mode="Tournament", tournament_size=4)
    rect = layout.settings_tournament_slot_toggle_rect(8, 6)  # only reachable at the 8-slot preset
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)

    handle_settings_event(event, ui_state)

    assert ui_state.tournament_slot_is_bot[6] is False


def test_settings_tournament_slot_click_ignored_outside_tournament_mode():
    ui_state = UIState(selected_game_mode="Single")
    rect = layout.settings_tournament_slot_toggle_rect(ui_state.tournament_size, 0)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)

    handle_settings_event(event, ui_state)

    assert ui_state.tournament_slot_is_bot[0] is False


def test_build_tournament_participants_names_humans_and_bots_independently():
    ui_state = UIState(tournament_size=4)
    ui_state.tournament_slot_is_bot[1] = True
    ui_state.tournament_slot_difficulty[1] = "Greedy"
    ui_state.tournament_slot_is_bot[3] = True
    ui_state.tournament_slot_difficulty[3] = "Blocking"

    participants = build_tournament_participants(ui_state)

    assert [p.name for p in participants] == ["Player 1", "Bot 1 (Greedy)", "Player 2", "Bot 2 (Blocking)"]
    assert [p.is_bot for p in participants] == [False, True, False, True]


def _bracket(n=4):
    participants = [Participant(name=f"Player {i + 1}") for i in range(n)]
    return Bracket(participants=participants, series_length=3, board_size=6, skip_limit=3)


def test_apply_match_identity_sets_names_and_bot_seats_for_a_mixed_match():
    participants = [
        Participant(name="Player 1"),
        Participant(name="Bot 1 (Greedy)", is_bot=True, bot_difficulty="Greedy"),
    ]
    tournament = Bracket(
        participants=participants, series_length=3, board_size=6, skip_limit=3, rng=ScriptedRandom([0])
    )
    match = tournament.current_match()
    series = tournament.new_series_for_current_match()
    game = series.new_game()
    ui_state = UIState()

    apply_match_identity(game, tournament, match, ui_state)

    a_name = game.players[PLAYER_1].name
    b_name = game.players[PLAYER_2].name
    assert {a_name, b_name} == {"Player 1", "Bot 1 (Greedy)"}
    bot_seat = PLAYER_1 if a_name == "Bot 1 (Greedy)" else PLAYER_2
    assert ui_state.active_bot_seats == {bot_seat: "Greedy"}


def test_handle_tournament_event_begin_button_requests_first_match():
    tournament = _bracket()
    ui_state = UIState(screen=Screen.TOURNAMENT)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.TOURNAMENT_ACTION_BUTTON_RECT.center)

    assert handle_tournament_event(event, ui_state, tournament) is True
    assert ui_state.begin_match_requested is True


def test_handle_tournament_event_back_button_mid_tournament_returns_to_playing():
    tournament = _bracket()
    match = tournament.current_match()
    match.series = tournament.new_series_for_current_match()
    ui_state = UIState(screen=Screen.TOURNAMENT)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.TOURNAMENT_ACTION_BUTTON_RECT.center)

    assert handle_tournament_event(event, ui_state, tournament) is True
    assert ui_state.screen == Screen.PLAYING


def test_handle_tournament_event_new_tournament_button_when_complete():
    tournament = _bracket(n=2)
    match = tournament.current_match()
    match.series = tournament.new_series_for_current_match()
    match.winner = match.participant_a
    tournament.advance()
    assert tournament.is_complete()

    ui_state = UIState(screen=Screen.TOURNAMENT)
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.TOURNAMENT_ACTION_BUTTON_RECT.center)

    assert handle_tournament_event(event, ui_state, tournament) is True
    assert ui_state.screen == Screen.MODE_SELECT


def test_is_bots_turn_generalizes_to_either_seat_via_active_bot_seats():
    from rectangles.ui.input import is_bots_turn

    game = Game(board_size=6)
    ui_state = UIState(active_bot_seats={PLAYER_1: "Basic"})
    assert is_bots_turn(game, ui_state) is True

    game.current_player_id = PLAYER_2
    assert is_bots_turn(game, ui_state) is False
