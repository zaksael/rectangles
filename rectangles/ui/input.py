from __future__ import annotations

import pygame

from ..constants import PLAYER_2
from ..game import Game, TurnState
from . import layout
from .state import ConfirmAction, Screen, UIState


def compute_top_left(game: Game, w: int, h: int, cell: tuple[int, int]) -> tuple[int, int]:
    r, c = cell
    if game.current_player_id == PLAYER_2:
        r -= h - 1
        c -= w - 1
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


def _request_quit(game: Game | None, ui_state: UIState) -> bool:
    if (
        ui_state.screen == Screen.PLAYING
        and game is not None
        and game.state != TurnState.GAME_OVER
        and game.history
    ):
        ui_state.pending_confirmation = ConfirmAction.EXIT
        return True
    return False


def _roll_dice(game: Game, ui_state: UIState) -> None:
    a, b = game.roll_dice()
    if game.state == TurnState.CHOOSING_PLACEMENT:
        ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)


def _continue_turn(game: Game) -> None:
    if not game.check_game_over():
        game.end_turn()


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


def _handle_left_click(pos: tuple[int, int], game: Game, ui_state: UIState) -> bool:
    if game.state == TurnState.GAME_OVER:
        if layout.GAME_OVER_NEW_GAME_BUTTON_RECT.collidepoint(pos):
            _new_game(ui_state)
        elif layout.GAME_OVER_EXIT_BUTTON_RECT.collidepoint(pos):
            return False
        return True

    if layout.NEW_GAME_BUTTON_RECT.collidepoint(pos):
        _request_new_game(game, ui_state)
        return True

    if game.state == TurnState.AWAITING_ROLL:
        if layout.ROLL_BUTTON_RECT.collidepoint(pos):
            _roll_dice(game, ui_state)
        return True

    if game.state == TurnState.SKIPPED:
        if layout.CONTINUE_BUTTON_RECT.collidepoint(pos):
            _continue_turn(game)
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


def _handle_settings_left_click(pos: tuple[int, int], ui_state: UIState) -> bool:
    for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_board_size = value
            return True
    for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_skip_limit = value
            return True
    if layout.SETTINGS_START_BUTTON_RECT.collidepoint(pos):
        _start_game(ui_state)
        return True
    if layout.SETTINGS_EXIT_BUTTON_RECT.collidepoint(pos):
        return False
    return True


def handle_settings_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_SPACE:
            _start_game(ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_settings_left_click(event.pos, ui_state)
    return True


def _handle_keydown(event: pygame.event.Event, game: Game, ui_state: UIState) -> bool:
    if game.state == TurnState.GAME_OVER:
        if event.key == pygame.K_n:
            _new_game(ui_state)
        elif event.key == pygame.K_ESCAPE:
            return False
        return True

    if event.key == pygame.K_n:
        _request_new_game(game, ui_state)
    elif event.key == pygame.K_r and game.state == TurnState.CHOOSING_PLACEMENT:
        _rotate(ui_state)
    elif event.key == pygame.K_d and game.state == TurnState.AWAITING_ROLL:
        _roll_dice(game, ui_state)
    elif event.key == pygame.K_SPACE and game.state == TurnState.SKIPPED:
        _continue_turn(game)
    return True


def _handle_confirm_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    action = ui_state.pending_confirmation
    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_RETURN, pygame.K_y):
            ui_state.pending_confirmation = None
            return _new_game_or_quit(action, ui_state)
        if event.key == pygame.K_ESCAPE:
            ui_state.pending_confirmation = None
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if layout.CONFIRM_YES_BUTTON_RECT.collidepoint(event.pos):
            ui_state.pending_confirmation = None
            return _new_game_or_quit(action, ui_state)
        if layout.CONFIRM_NO_BUTTON_RECT.collidepoint(event.pos):
            ui_state.pending_confirmation = None
    return True


def _new_game_or_quit(action: ConfirmAction | None, ui_state: UIState) -> bool:
    if action == ConfirmAction.NEW_GAME:
        _new_game(ui_state)
        return True
    return False  # ConfirmAction.EXIT


def handle_event(event: pygame.event.Event, game: Game, ui_state: UIState) -> bool:
    if ui_state.pending_confirmation is not None:
        return _handle_confirm_event(event, ui_state)
    if event.type == pygame.QUIT:
        return _request_quit(game, ui_state)
    if event.type == pygame.KEYDOWN:
        if not _handle_keydown(event, game, ui_state):
            return False
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            if not _handle_left_click(event.pos, game, ui_state):
                return False
        elif event.button == 3 and game.state == TurnState.CHOOSING_PLACEMENT:
            _rotate(ui_state)
    return True
