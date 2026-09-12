from __future__ import annotations

import pygame

from .. import persistence
from . import layout
from .input_common import _design_pos
from .state import Screen, UIState


def _start_game(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.game_requested = True
    persistence.delete_save()


def _start_series(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.series_requested = True
    persistence.delete_save()


def _start_tournament(ui_state: UIState) -> None:
    ui_state.screen = Screen.TOURNAMENT
    ui_state.tournament_requested = True
    persistence.delete_save()


_MODE_STARTERS = {"Single": _start_game, "Series": _start_series, "Tournament": _start_tournament}


def _start_selected_mode(ui_state: UIState) -> None:
    _MODE_STARTERS[ui_state.selected_game_mode](ui_state)


def _handle_settings_left_click(pos: tuple[int, int], ui_state: UIState) -> bool:
    mode = ui_state.selected_game_mode
    tournament_size = ui_state.tournament_size
    for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_board_size = value
            return True
    for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_skip_limit = value
            return True
    if mode != "Tournament":
        for value, rect in layout.settings_opponent_button_rects(mode, tournament_size).items():
            if rect.collidepoint(pos):
                ui_state.selected_bot_enabled = value != "Human"
                if value != "Human":
                    ui_state.selected_bot_difficulty = value
                return True
    if mode != "Single":
        for value, rect in layout.settings_series_length_button_rects(mode, tournament_size).items():
            if rect.collidepoint(pos):
                ui_state.selected_series_length = value
                return True
    if mode == "Tournament":
        for value, rect in layout.settings_tournament_size_button_rects(tournament_size).items():
            if rect.collidepoint(pos):
                ui_state.tournament_size = value
                ui_state.settings_scroll = min(ui_state.settings_scroll, layout.settings_max_scroll(mode, value))
                return True
        for i in range(tournament_size):
            if layout.settings_tournament_slot_toggle_rect(tournament_size, i).collidepoint(pos):
                ui_state.tournament_slot_is_bot[i] = not ui_state.tournament_slot_is_bot[i]
                return True
            if ui_state.tournament_slot_is_bot[i]:
                for value, rect in layout.settings_tournament_slot_difficulty_rects(tournament_size, i).items():
                    if rect.collidepoint(pos):
                        ui_state.tournament_slot_difficulty[i] = value
                        return True
    if layout.settings_all_rules_button_rect(mode, tournament_size).collidepoint(pos):
        ui_state.toggle_all_house_rules()
        return True
    chip_rects = layout.settings_house_rule_button_rects(mode, tournament_size)
    for label, toggle_attr in (
        ("Prize", "selected_prize_enabled"),
        ("Walls", "selected_walls_enabled"),
        ("Obstacles", "selected_obstacles_enabled"),
        ("Pitfall", "selected_pitfall_enabled"),
        ("Steal", "selected_steal_enabled"),
        ("Wildcard", "selected_wildcard_enabled"),
        ("Enclosure", "selected_self_enclosed_penalty_enabled"),
        ("Reroll", "selected_reroll_enabled"),
        ("Comeback", "selected_comeback_nudge_enabled"),
    ):
        if chip_rects[label].collidepoint(pos):
            if label in ("Wildcard", "Reroll") and ui_state.wildcard_reroll_locked:
                return True
            setattr(ui_state, toggle_attr, not getattr(ui_state, toggle_attr))
            return True
    if layout.settings_start_button_rect(mode, tournament_size).collidepoint(pos):
        _start_selected_mode(ui_state)
        return True
    if layout.settings_back_button_rect(mode, tournament_size).collidepoint(pos):
        ui_state.screen = Screen.MODE_SELECT
        return True
    if layout.settings_exit_button_rect(mode, tournament_size).collidepoint(pos):
        return False
    return True


def _handle_settings_mousewheel(event: pygame.event.Event, ui_state: UIState) -> None:
    max_scroll = layout.settings_max_scroll(ui_state.selected_game_mode, ui_state.tournament_size)
    ui_state.settings_scroll = max(0, min(ui_state.settings_scroll - event.y * 40, max_scroll))


def handle_settings_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            ui_state.screen = Screen.MODE_SELECT
        elif event.key == pygame.K_SPACE:
            _start_selected_mode(ui_state)
    if event.type == pygame.MOUSEWHEEL:
        _handle_settings_mousewheel(event, ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # Map to design coords, then add the scroll offset (rects are in
        # unscrolled content space) before hit-testing.
        design_x, design_y = _design_pos(event.pos)
        pos = (design_x, design_y + ui_state.settings_scroll)
        return _handle_settings_left_click(pos, ui_state)
    return True
