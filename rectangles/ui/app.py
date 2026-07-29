from __future__ import annotations

import os

import pygame

from .. import persistence
from ..game import Game, TurnState
from ..series import Series
from . import input as game_input
from . import layout
from .renderer import Renderer
from .state import Screen, UIState

FPS = 60
AUTO_ACTION_DELAY_MS = 500

# On macOS Retina displays, SDL2 otherwise gives the window a backing store
# at 2x the requested size (for a crisp image) while mouse events keep
# reporting the logical (1x) coordinates our layout rects are defined in -
# without this, that mismatch shrinks every button's effective clickable
# area down toward its center. Must be set before pygame.init().
os.environ.setdefault("SDL_VIDEO_HIGHDPI_DISABLED", "1")


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Rectangles")
    screen = pygame.display.set_mode((layout.WINDOW_WIDTH, layout.WINDOW_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    game: Game | None = None
    series: Series | None = None
    series_game_recorded = False
    auto_action_at = 0
    ui_state = UIState()
    renderer = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                # Width is pinned (every board/settings/panel column position
                # assumes it) - only the requested height is honored.
                height = max(event.h, layout.MIN_WINDOW_HEIGHT)
                screen = pygame.display.set_mode((layout.WINDOW_WIDTH, height), pygame.RESIZABLE)
                renderer.resize(screen)
                continue
            if ui_state.screen == Screen.SETTINGS:
                if not game_input.handle_settings_event(event, ui_state):
                    running = False
            elif ui_state.screen == Screen.REPLAY:
                if not game_input.handle_replay_event(event, ui_state, game):
                    running = False
            else:
                if not game_input.handle_event(event, game, ui_state, series):
                    running = False

        if ui_state.game_requested:
            game = Game(
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
                doubles_enabled=ui_state.selected_doubles_enabled,
                flag_conquest_enabled=ui_state.selected_flag_conquest_enabled,
                flag_bonus_points=ui_state.selected_flag_bonus_points,
                walls_enabled=ui_state.selected_walls_enabled,
                wildcard_enabled=ui_state.selected_wildcard_enabled,
            )
            series = None
            series_game_recorded = False
            auto_action_at = 0
            ui_state.game_requested = False

        if ui_state.series_requested:
            series = Series(
                length=ui_state.selected_series_length,
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
                doubles_enabled=ui_state.selected_doubles_enabled,
                flag_conquest_enabled=ui_state.selected_flag_conquest_enabled,
                flag_bonus_points=ui_state.selected_flag_bonus_points,
                walls_enabled=ui_state.selected_walls_enabled,
                wildcard_enabled=ui_state.selected_wildcard_enabled,
            )
            game = series.new_game()
            series_game_recorded = False
            auto_action_at = 0
            ui_state.series_requested = False

        if ui_state.resume_requested:
            loaded = persistence.load_game()
            if loaded is None:
                ui_state.screen = Screen.SETTINGS
            else:
                game, series = loaded
            series_game_recorded = False
            auto_action_at = 0
            ui_state.resume_requested = False

        if ui_state.next_game_requested:
            game = series.new_game()
            series_game_recorded = False
            auto_action_at = 0
            ui_state.next_game_requested = False

        if series is not None and game is not None and game.state == TurnState.GAME_OVER and not series_game_recorded:
            series.record_game(game)
            series_game_recorded = True

        if (
            ui_state.screen == Screen.PLAYING
            and game is not None
            and game.state != TurnState.GAME_OVER
            and ui_state.pending_confirmation is None
            and pygame.time.get_ticks() >= auto_action_at
        ):
            if game_input.is_bots_turn(game, ui_state):
                game_input.take_bot_turn(game, ui_state)
                auto_action_at = pygame.time.get_ticks() + AUTO_ACTION_DELAY_MS
            elif game.state == TurnState.SKIPPED:
                game_input.continue_turn(game)
                auto_action_at = pygame.time.get_ticks() + AUTO_ACTION_DELAY_MS

        if ui_state.screen == Screen.PLAYING and not game_input.is_bots_turn(game, ui_state):
            game_input.update_hover(game, ui_state)

        renderer.draw(game, ui_state, series)
        clock.tick(FPS)

    if persistence.should_save_on_exit(game, series):
        persistence.save_game(game, series)

    pygame.quit()
