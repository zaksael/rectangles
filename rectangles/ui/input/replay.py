from __future__ import annotations

import pygame

from ...engine.constants import REPLAY_SPEED_PRESETS
from ...engine.game import Game
from .. import layout
from .common import _design_pos
from ..state import Screen, UIState


def _clamp_replay_step(ui_state: UIState, game: Game) -> None:
    ui_state.replay_step = max(0, min(ui_state.replay_step, len(game.history)))


def handle_replay_event(event: pygame.event.Event, ui_state: UIState, game: Game) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        # Any keyboard nav takes manual control and stops autoplay.
        ui_state.replay_autoplay = False
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
        pos = _design_pos(event.pos)
        rects = layout.REPLAY_BUTTON_RECTS
        if any(rects[k].collidepoint(pos) for k in ("first", "prev", "next", "last")):
            ui_state.replay_autoplay = False
        if rects["first"].collidepoint(pos):
            ui_state.replay_step = 0
        elif rects["prev"].collidepoint(pos):
            ui_state.replay_step -= 1
        elif rects["next"].collidepoint(pos):
            ui_state.replay_step += 1
        elif rects["last"].collidepoint(pos):
            ui_state.replay_step = len(game.history)
        elif rects["play"].collidepoint(pos):
            ui_state.replay_autoplay = not ui_state.replay_autoplay
        elif rects["back"].collidepoint(pos):
            ui_state.screen = Screen.PLAYING
        elif layout.REPLAY_REVEAL_BUTTON_RECT.collidepoint(pos):
            ui_state.replay_show_better_option = not ui_state.replay_show_better_option
        else:
            for value in REPLAY_SPEED_PRESETS:
                if rects[value].collidepoint(pos):
                    ui_state.replay_speed = value
                    break
        _clamp_replay_step(ui_state, game)
    return True
