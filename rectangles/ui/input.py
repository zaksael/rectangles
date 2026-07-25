from __future__ import annotations

import pygame

from ..constants import PLAYER_2
from ..game import Game, TurnState
from . import layout
from .state import Screen, UIState


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
    if layout.NEW_GAME_BUTTON_RECT.collidepoint(pos):
        ui_state.reset()
        ui_state.screen = Screen.SETTINGS
        return True

    if game.state == TurnState.GAME_OVER:
        if layout.GAME_OVER_NEW_GAME_BUTTON_RECT.collidepoint(pos):
            ui_state.reset()
            ui_state.screen = Screen.SETTINGS
        elif layout.GAME_OVER_EXIT_BUTTON_RECT.collidepoint(pos):
            return False
        return True

    if game.state == TurnState.AWAITING_ROLL:
        if layout.ROLL_BUTTON_RECT.collidepoint(pos):
            a, b = game.roll_dice()
            if game.state == TurnState.CHOOSING_PLACEMENT:
                ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)
        return True

    if game.state == TurnState.SKIPPED:
        if layout.CONTINUE_BUTTON_RECT.collidepoint(pos):
            if not game.check_game_over():
                game.end_turn()
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
        ui_state.screen = Screen.PLAYING
        ui_state.game_requested = True
        return True
    if layout.SETTINGS_EXIT_BUTTON_RECT.collidepoint(pos):
        return False
    return True


def handle_settings_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_settings_left_click(event.pos, ui_state)
    return True


def handle_event(event: pygame.event.Event, game: Game, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
        if game.state == TurnState.CHOOSING_PLACEMENT:
            _rotate(ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            if not _handle_left_click(event.pos, game, ui_state):
                return False
        elif event.button == 3 and game.state == TurnState.CHOOSING_PLACEMENT:
            _rotate(ui_state)
    return True
