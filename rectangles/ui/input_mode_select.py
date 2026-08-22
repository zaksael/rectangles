from __future__ import annotations

import pygame

from .. import persistence
from . import layout
from .input_common import _design_pos
from .state import Screen, UIState


def _select_game_mode(ui_state: UIState, mode: str) -> None:
    ui_state.selected_game_mode = mode
    ui_state.screen = Screen.SETTINGS
    ui_state.settings_scroll = 0


def _resume_game(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.resume_requested = True


def handle_mode_select_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_r and persistence.has_save():
            _resume_game(ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = _design_pos(event.pos)
        for mode, rect in layout.MODE_SELECT_BUTTON_RECTS.items():
            if rect.collidepoint(pos):
                _select_game_mode(ui_state, mode)
                return True
        if persistence.has_save() and layout.MODE_SELECT_RESUME_BUTTON_RECT.collidepoint(pos):
            _resume_game(ui_state)
            return True
        if layout.MODE_SELECT_EXIT_BUTTON_RECT.collidepoint(pos):
            return False
    return True
