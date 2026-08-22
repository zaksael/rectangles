from __future__ import annotations

import pygame

from ..tournament import Bracket
from . import layout
from .input_common import _design_pos, _new_game
from .state import Screen, UIState


def handle_tournament_event(event: pygame.event.Event, ui_state: UIState, tournament: Bracket) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        match = tournament.current_match()
        if not tournament.is_complete() and match is not None and match.series is not None:
            ui_state.screen = Screen.PLAYING
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = _design_pos(event.pos)
        if layout.TOURNAMENT_ACTION_BUTTON_RECT.collidepoint(pos):
            if tournament.is_complete():
                _new_game(ui_state)
            else:
                match = tournament.current_match()
                if match.series is None:
                    ui_state.begin_match_requested = True
                else:
                    ui_state.screen = Screen.PLAYING
    return True
