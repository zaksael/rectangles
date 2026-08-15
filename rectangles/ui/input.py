from __future__ import annotations

import pygame

from .. import bot, persistence
from ..constants import DICE_MAX, DICE_MIN, PLAYER_2
from ..game import Game, TurnState
from ..series import Series
from . import layout
from .state import ConfirmAction, Screen, UIState


def _current_window_size() -> tuple[int, int]:
    # The real window can be resized (see ui/app.py's VIDEORESIZE handling), so
    # click/scroll hit-testing against window-size-dependent layout rects needs
    # the live size, not the static layout.WINDOW_WIDTH/HEIGHT defaults. Falls
    # back to those defaults when no display exists yet (e.g. headless tests).
    surface = pygame.display.get_surface()
    return surface.get_size() if surface is not None else (layout.WINDOW_WIDTH, layout.WINDOW_HEIGHT)


def compute_top_left(game: Game, w: int, h: int, cell: tuple[int, int]) -> tuple[int, int]:
    r, c = cell
    r -= h // 2
    c -= w // 2
    r = max(0, min(r, game.board.size - h))
    c = max(0, min(c, game.board.size - w))
    return (r, c)


def _rotate(ui_state: UIState) -> None:
    if ui_state.current_dims is None:
        return
    w, h = ui_state.current_dims
    ui_state.current_dims = (h, w)


def _new_game(ui_state: UIState) -> None:
    ui_state.reset()
    ui_state.screen = Screen.SETTINGS


def _request_new_game(game: Game, ui_state: UIState) -> None:
    if game.history:
        ui_state.pending_confirmation = ConfirmAction.NEW_GAME
    else:
        _new_game(ui_state)


def _request_surrender(ui_state: UIState) -> None:
    ui_state.pending_confirmation = ConfirmAction.SURRENDER


def _request_quit(game: Game | None, ui_state: UIState) -> bool:
    if ui_state.screen == Screen.PLAYING and persistence.has_game_in_progress(game):
        ui_state.pending_confirmation = ConfirmAction.EXIT
        return True
    return False


def _roll_dice(game: Game, ui_state: UIState) -> None:
    a, b = game.roll_dice()
    if game.state == TurnState.CHOOSING_PLACEMENT:
        ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)


def _choose_wildcard_value(game: Game, ui_state: UIState, value: int) -> None:
    game.choose_wildcard_value(value)
    if game.state == TurnState.CHOOSING_PLACEMENT:
        a, b = game.last_roll
        ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)


def continue_turn(game: Game) -> None:
    if not game.check_game_over():
        game.end_turn()


def is_bots_turn(game: Game, ui_state: UIState) -> bool:
    return ui_state.selected_bot_enabled and game.current_player_id == PLAYER_2


def take_bot_turn(game: Game, ui_state: UIState) -> None:
    if game.state == TurnState.AWAITING_ROLL:
        _roll_dice(game, ui_state)
    elif game.state == TurnState.CHOOSING_WILDCARD:
        # Bot always picks uniformly at random, independent of difficulty -
        # Greedy/Blocking only affect placement choice, not this.
        _choose_wildcard_value(game, ui_state, game.rng.randint(DICE_MIN, DICE_MAX))
    elif game.state == TurnState.SKIPPED:
        continue_turn(game)
    elif game.state == TurnState.CHOOSING_PLACEMENT:
        top_left, w, h = bot.choose_placement(game, ui_state.selected_bot_difficulty)
        if game.attempt_place(top_left, w, h):
            if not game.check_game_over():
                game.end_turn()
            ui_state.reset()


def update_hover(game: Game, ui_state: UIState) -> None:
    if game.state != TurnState.CHOOSING_PLACEMENT or ui_state.current_dims is None:
        ui_state.hover_top_left = None
        return
    cell = layout.pixel_to_cell(*pygame.mouse.get_pos(), game.board.size)
    if cell is None:
        ui_state.hover_top_left = None
        return
    w, h = ui_state.current_dims
    top_left = compute_top_left(game, w, h, cell)
    ui_state.hover_top_left = top_left
    ui_state.hover_legal = top_left in game.legal_cache.get((w, h), set())


def _advance_or_end_series(series: Series | None, ui_state: UIState) -> None:
    if series is not None and not series.is_complete():
        ui_state.next_game_requested = True
    else:
        _new_game(ui_state)


def _clamp_replay_step(ui_state: UIState, game: Game) -> None:
    ui_state.replay_step = max(0, min(ui_state.replay_step, len(game.history)))


def handle_replay_event(event: pygame.event.Event, ui_state: UIState, game: Game) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            ui_state.screen = Screen.PLAYING
        elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
            ui_state.replay_step += 1
        elif event.key in (pygame.K_LEFT, pygame.K_UP):
            ui_state.replay_step -= 1
        elif event.key == pygame.K_HOME:
            ui_state.replay_step = 0
        elif event.key == pygame.K_END:
            ui_state.replay_step = len(game.history)
        _clamp_replay_step(ui_state, game)
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        window_width, window_height = _current_window_size()
        rects = layout.replay_button_rects(window_width, window_height)
        if rects["first"].collidepoint(event.pos):
            ui_state.replay_step = 0
        elif rects["prev"].collidepoint(event.pos):
            ui_state.replay_step -= 1
        elif rects["next"].collidepoint(event.pos):
            ui_state.replay_step += 1
        elif rects["last"].collidepoint(event.pos):
            ui_state.replay_step = len(game.history)
        elif rects["back"].collidepoint(event.pos):
            ui_state.screen = Screen.PLAYING
        _clamp_replay_step(ui_state, game)
    return True


def _handle_left_click(pos: tuple[int, int], game: Game, ui_state: UIState, series: Series | None) -> bool:
    window_width, window_height = _current_window_size()
    if game.state == TurnState.GAME_OVER:
        if layout.game_over_new_game_button_rect(window_width, window_height).collidepoint(pos):
            _advance_or_end_series(series, ui_state)
        elif layout.game_over_replay_button_rect(window_width, window_height).collidepoint(pos):
            ui_state.screen = Screen.REPLAY
            ui_state.replay_step = 0
        elif layout.game_over_exit_button_rect(window_width, window_height).collidepoint(pos):
            return False
        return True

    if layout.new_game_button_rect(window_height).collidepoint(pos):
        _request_new_game(game, ui_state)
        return True

    if layout.exit_button_rect(window_height).collidepoint(pos):
        return _request_quit(game, ui_state)

    if layout.surrender_button_rect(window_height).collidepoint(pos):
        _request_surrender(ui_state)
        return True

    if is_bots_turn(game, ui_state):
        return True

    if game.state == TurnState.AWAITING_ROLL:
        if layout.ROLL_BUTTON_RECT.collidepoint(pos):
            _roll_dice(game, ui_state)
        return True

    if game.state == TurnState.CHOOSING_WILDCARD:
        # Not gated on wildcard_value_is_legal(): an illegal value still
        # needs to be choosable so the turn can resolve into its legitimate
        # skip - if every value happened to be illegal, gating here would
        # leave no button clickable at all, soft-locking the turn.
        for value, rect in layout.WILDCARD_VALUE_BUTTON_RECTS.items():
            if rect.collidepoint(pos):
                _choose_wildcard_value(game, ui_state, value)
                break
        return True

    if game.state == TurnState.SKIPPED:
        if layout.CONTINUE_BUTTON_RECT.collidepoint(pos):
            continue_turn(game)
        return True

    if game.state == TurnState.CHOOSING_PLACEMENT:
        if layout.ROTATE_BUTTON_RECT.collidepoint(pos):
            _rotate(ui_state)
            return True
        cell = layout.pixel_to_cell(*pos, game.board.size)
        if cell is None or ui_state.current_dims is None:
            return True
        w, h = ui_state.current_dims
        top_left = compute_top_left(game, w, h, cell)
        if game.attempt_place(top_left, w, h):
            if not game.check_game_over():
                game.end_turn()
            ui_state.reset()
        return True

    return True


def _start_game(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.game_requested = True
    persistence.delete_save()


def _start_series(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.series_requested = True
    persistence.delete_save()


def _resume_game(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.resume_requested = True


def _handle_settings_left_click(pos: tuple[int, int], ui_state: UIState) -> bool:
    for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_board_size = value
            return True
    for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_skip_limit = value
            return True
    if layout.SETTINGS_FLAG_CONQUEST_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_flag_conquest_enabled = not ui_state.selected_flag_conquest_enabled
        return True
    if layout.SETTINGS_WALLS_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_walls_enabled = not ui_state.selected_walls_enabled
        return True
    if layout.SETTINGS_OBSTACLES_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_obstacles_enabled = not ui_state.selected_obstacles_enabled
        return True
    if layout.SETTINGS_WILDCARD_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_wildcard_enabled = not ui_state.selected_wildcard_enabled
        return True
    if layout.SETTINGS_SELF_ENCLOSED_PENALTY_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_self_enclosed_penalty_enabled = not ui_state.selected_self_enclosed_penalty_enabled
        return True
    if layout.SETTINGS_ALL_RULES_BUTTON_RECT.collidepoint(pos):
        ui_state.toggle_all_house_rules()
        return True
    if layout.SETTINGS_BOT_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_bot_enabled = not ui_state.selected_bot_enabled
        return True
    if ui_state.selected_bot_enabled:
        for value, rect in layout.SETTINGS_BOT_DIFFICULTY_BUTTON_RECTS.items():
            if rect.collidepoint(pos):
                ui_state.selected_bot_difficulty = value
                return True
    for value, rect in layout.SETTINGS_SERIES_LENGTH_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_series_length = value
            return True
    if layout.SETTINGS_START_BUTTON_RECT.collidepoint(pos):
        _start_game(ui_state)
        return True
    if layout.SETTINGS_START_SERIES_BUTTON_RECT.collidepoint(pos):
        _start_series(ui_state)
        return True
    if persistence.has_save() and layout.SETTINGS_RESUME_BUTTON_RECT.collidepoint(pos):
        _resume_game(ui_state)
        return True
    if layout.SETTINGS_EXIT_BUTTON_RECT.collidepoint(pos):
        return False
    return True


def _handle_settings_mousewheel(event: pygame.event.Event, ui_state: UIState) -> None:
    _, window_height = _current_window_size()
    max_scroll = layout.settings_max_scroll(window_height)
    ui_state.settings_scroll = max(0, min(ui_state.settings_scroll - event.y * 40, max_scroll))


def handle_settings_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_SPACE:
            _start_game(ui_state)
        elif event.key == pygame.K_r and persistence.has_save():
            _resume_game(ui_state)
    if event.type == pygame.MOUSEWHEEL:
        _handle_settings_mousewheel(event, ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # Click positions are in real-window coordinates; the settings
        # content itself may be scrolled up within a taller virtual surface
        # (see Renderer._settings_surface), so translate back before hit-testing.
        pos = (event.pos[0], event.pos[1] + ui_state.settings_scroll)
        return _handle_settings_left_click(pos, ui_state)
    return True


def _handle_keydown(event: pygame.event.Event, game: Game, ui_state: UIState, series: Series | None) -> bool:
    if game.state == TurnState.GAME_OVER:
        if event.key == pygame.K_n:
            _advance_or_end_series(series, ui_state)
        elif event.key == pygame.K_ESCAPE:
            return False
        return True

    if event.key == pygame.K_n:
        _request_new_game(game, ui_state)
    elif event.key == pygame.K_ESCAPE:
        return _request_quit(game, ui_state)
    elif event.key == pygame.K_s:
        _request_surrender(ui_state)
    elif event.key == pygame.K_r and game.state == TurnState.CHOOSING_PLACEMENT and not is_bots_turn(
        game, ui_state
    ):
        _rotate(ui_state)
    elif event.key == pygame.K_d and game.state == TurnState.AWAITING_ROLL and not is_bots_turn(game, ui_state):
        _roll_dice(game, ui_state)
    elif event.key == pygame.K_SPACE and game.state == TurnState.SKIPPED and not is_bots_turn(game, ui_state):
        continue_turn(game)
    return True


def _handle_confirm_event(event: pygame.event.Event, game: Game, ui_state: UIState) -> bool:
    action = ui_state.pending_confirmation
    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_RETURN, pygame.K_y):
            ui_state.pending_confirmation = None
            return _resolve_confirmation(action, game, ui_state)
        if event.key == pygame.K_ESCAPE:
            ui_state.pending_confirmation = None
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        window_width, window_height = _current_window_size()
        if layout.confirm_yes_button_rect(window_width, window_height).collidepoint(event.pos):
            ui_state.pending_confirmation = None
            return _resolve_confirmation(action, game, ui_state)
        if layout.confirm_no_button_rect(window_width, window_height).collidepoint(event.pos):
            ui_state.pending_confirmation = None
    return True


def _resolve_confirmation(action: ConfirmAction | None, game: Game, ui_state: UIState) -> bool:
    if action == ConfirmAction.NEW_GAME:
        _new_game(ui_state)
        return True
    if action == ConfirmAction.SURRENDER:
        game.surrender()
        return True
    return False  # ConfirmAction.EXIT


def _handle_mousewheel(event: pygame.event.Event, game: Game, ui_state: UIState) -> None:
    if not layout.PANEL_HISTORY_REGION_RECT.collidepoint(pygame.mouse.get_pos()):
        return
    max_offset = max(0, len(game.history) - layout.PANEL_HISTORY_MAX_ROWS)
    ui_state.history_scroll = max(0, min(ui_state.history_scroll + event.y, max_offset))


def handle_event(event: pygame.event.Event, game: Game, ui_state: UIState, series: Series | None = None) -> bool:
    if ui_state.pending_confirmation is not None:
        return _handle_confirm_event(event, game, ui_state)
    if event.type == pygame.QUIT:
        return _request_quit(game, ui_state)
    if event.type == pygame.KEYDOWN:
        if not _handle_keydown(event, game, ui_state, series):
            return False
    if event.type == pygame.MOUSEWHEEL:
        _handle_mousewheel(event, game, ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            if not _handle_left_click(event.pos, game, ui_state, series):
                return False
        elif event.button == 3 and game.state == TurnState.CHOOSING_PLACEMENT and not is_bots_turn(
            game, ui_state
        ):
            _rotate(ui_state)
    return True
