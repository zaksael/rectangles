import pygame

from rectangles import persistence
from rectangles.constants import (
    BOARD_SIZE_PRESETS,
    FLAG_BONUS_POINTS_PRESETS,
    PLAYER_1,
    PLAYER_2,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
)
from rectangles.game import Game, TurnState
from rectangles.series import Series
from rectangles.ui import layout
from rectangles.ui.input import (
    compute_top_left,
    handle_event,
    handle_settings_event,
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


def test_compute_top_left_p1_uses_cell_directly():
    game = Game(board_size=6)
    assert compute_top_left(game, w=2, h=2, cell=(2, 3)) == (2, 3)


def test_compute_top_left_p1_clamps_upper_bound():
    game = Game(board_size=6)
    # A 2x2 piece anchored at (5, 5) would overrun the board; clamp to fit.
    assert compute_top_left(game, w=2, h=2, cell=(5, 5)) == (4, 4)


def test_compute_top_left_p2_uses_cell_as_bottom_right():
    game = Game(board_size=6)
    game.current_player_id = PLAYER_2
    # A 2x2 piece with bottom-right at (5, 5) has top-left at (4, 4).
    assert compute_top_left(game, w=2, h=2, cell=(5, 5)) == (4, 4)


def test_compute_top_left_p2_clamps_lower_bound():
    game = Game(board_size=6)
    game.current_player_id = PLAYER_2
    # A 3x3 piece with bottom-right at (0, 0) would go negative; clamp to fit.
    assert compute_top_left(game, w=3, h=3, cell=(0, 0)) == (0, 0)


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
    assert ui_state.screen == Screen.SETTINGS


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
    assert ui_state.screen == Screen.SETTINGS


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
    pos = layout.cell_rect(0, 0).center  # P1's start corner - anchors the first piece

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
    pos = layout.cell_rect(5, 5).center  # far from P1's start corner - not anchored, illegal

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
    # is skipped. (6, 6) is also doubles, granting a bonus turn.
    game = Game(board_size=4, doubles_enabled=True, rng=ScriptedRandom([6, 6]))
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
    assert game.current_player_id == PLAYER_1  # doubles: same player continues


def test_continue_button_click_on_skipped_ends_turn():
    game = _skipped_game()
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.CONTINUE_BUTTON_RECT.center)
    handle_event(event, game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert game.current_player_id == PLAYER_1


def test_take_bot_turn_rolls_when_awaiting_roll():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    ui_state = UIState()
    assert game.state == TurnState.AWAITING_ROLL

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.last_roll == (2, 3)


def test_take_bot_turn_continues_when_skipped():
    game = _skipped_game()
    ui_state = UIState()

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL


def test_take_bot_turn_places_when_choosing_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3, 0]))
    ui_state = UIState()
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT

    take_bot_turn(game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert len(game.players[PLAYER_1].pieces) == 1


def test_human_roll_click_ignored_during_bots_turn():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.current_player_id = PLAYER_2
    ui_state = UIState(screen=Screen.PLAYING, selected_bot_enabled=True)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.ROLL_BUTTON_RECT.center)
    handle_event(event, game, ui_state)

    assert game.state == TurnState.AWAITING_ROLL
    assert game.last_roll is None


def test_update_hover_sets_top_left_and_legal_flag(monkeypatch):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    ui_state = UIState(screen=Screen.PLAYING, current_dims=(2, 3))
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: layout.cell_rect(0, 0).center)

    update_hover(game, ui_state)

    assert ui_state.hover_top_left == (0, 0)
    assert ui_state.hover_legal is True


def test_update_hover_clears_outside_choosing_placement():
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING, hover_top_left=(1, 1))

    update_hover(game, ui_state)

    assert ui_state.hover_top_left is None


# --- Game-over navigation, with and without a series --------------------


def test_game_over_new_game_button_without_series_returns_to_settings():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.GAME_OVER_NEW_GAME_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state, series=None) is True

    assert ui_state.screen == Screen.SETTINGS


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


def test_game_over_new_game_button_with_completed_series_returns_to_settings():
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
    assert ui_state.screen == Screen.SETTINGS


def test_game_over_key_n_with_incomplete_series_requests_next_game():
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    ui_state = UIState(screen=Screen.PLAYING)

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
    assert handle_event(event, game, ui_state, series) is True

    assert ui_state.next_game_requested is True


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


# --- Confirmation dialog, mouse path -------------------------------------


def test_confirm_yes_button_click_performs_new_game():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.CONFIRM_YES_BUTTON_RECT.center)
    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.SETTINGS


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


def test_settings_escape_key_returns_false():
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    assert handle_settings_event(event, UIState()) is False


def test_settings_space_key_starts_game(monkeypatch):
    monkeypatch.setattr(persistence, "delete_save", lambda: None)
    ui_state = UIState()

    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.game_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_settings_r_key_resumes_only_when_a_save_exists(monkeypatch):
    ui_state = UIState()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r)

    monkeypatch.setattr(persistence, "has_save", lambda: False)
    handle_settings_event(event, ui_state)
    assert ui_state.resume_requested is False

    monkeypatch.setattr(persistence, "has_save", lambda: True)
    handle_settings_event(event, ui_state)
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


def test_settings_doubles_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_doubles_enabled is False

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_DOUBLES_BUTTON_RECT.center
    )
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_doubles_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_doubles_enabled is False


def test_settings_flag_conquest_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_flag_conquest_enabled is False

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_FLAG_CONQUEST_BUTTON_RECT.center
    )
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_flag_conquest_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_flag_conquest_enabled is False


def test_settings_flag_bonus_buttons_update_selection():
    ui_state = UIState(selected_flag_conquest_enabled=True)
    for value, rect in layout.SETTINGS_FLAG_BONUS_BUTTON_RECTS.items():
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.selected_flag_bonus_points == value
    assert set(layout.SETTINGS_FLAG_BONUS_BUTTON_RECTS) == set(FLAG_BONUS_POINTS_PRESETS)


def test_settings_flag_bonus_buttons_ignored_while_flag_conquest_disabled():
    ui_state = UIState()
    default_value = ui_state.selected_flag_bonus_points
    for value, rect in layout.SETTINGS_FLAG_BONUS_BUTTON_RECTS.items():
        if value == default_value:
            continue
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.selected_flag_bonus_points == default_value


def test_settings_bot_button_toggles_selection():
    ui_state = UIState()
    assert ui_state.selected_bot_enabled is False

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_BOT_BUTTON_RECT.center)
    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_bot_enabled is True

    assert handle_settings_event(event, ui_state) is True
    assert ui_state.selected_bot_enabled is False


def test_settings_series_length_buttons_update_selection():
    ui_state = UIState()
    for value, rect in layout.SETTINGS_SERIES_LENGTH_BUTTON_RECTS.items():
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center)
        assert handle_settings_event(event, ui_state) is True
        assert ui_state.selected_series_length == value
    assert set(layout.SETTINGS_SERIES_LENGTH_BUTTON_RECTS) == set(SERIES_LENGTH_PRESETS)


def test_settings_start_game_button_click_deletes_save_and_starts(monkeypatch):
    deleted = []
    monkeypatch.setattr(persistence, "delete_save", lambda: deleted.append(True))
    ui_state = UIState()

    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_START_BUTTON_RECT.center)
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.game_requested is True
    assert ui_state.screen == Screen.PLAYING
    assert deleted == [True]


def test_settings_start_series_button_click_starts_series(monkeypatch):
    monkeypatch.setattr(persistence, "delete_save", lambda: None)
    ui_state = UIState()

    event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_START_SERIES_BUTTON_RECT.center
    )
    assert handle_settings_event(event, ui_state) is True

    assert ui_state.series_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_settings_resume_button_click_only_when_a_save_exists(monkeypatch):
    ui_state = UIState()
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_RESUME_BUTTON_RECT.center)

    monkeypatch.setattr(persistence, "has_save", lambda: False)
    handle_settings_event(event, ui_state)
    assert ui_state.resume_requested is False

    monkeypatch.setattr(persistence, "has_save", lambda: True)
    handle_settings_event(event, ui_state)
    assert ui_state.resume_requested is True
    assert ui_state.screen == Screen.PLAYING


def test_settings_exit_button_click_returns_false():
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=layout.SETTINGS_EXIT_BUTTON_RECT.center)
    assert handle_settings_event(event, UIState()) is False
