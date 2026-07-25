from __future__ import annotations

import pygame

from .. import persistence
from ..game import Game, TurnState
from ..series import Series
from . import input as game_input
from . import layout
from .renderer import Renderer
from .state import Screen, UIState

FPS = 60


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Rectangles")
    screen = pygame.display.set_mode((layout.WINDOW_WIDTH, layout.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game: Game | None = None
    series: Series | None = None
    series_game_recorded = False
    ui_state = UIState()
    renderer = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if ui_state.screen == Screen.SETTINGS:
                if not game_input.handle_settings_event(event, ui_state):
                    running = False
            else:
                if not game_input.handle_event(event, game, ui_state, series):
                    running = False

        if ui_state.game_requested:
            game = Game(board_size=ui_state.selected_board_size, skip_limit=ui_state.selected_skip_limit)
            series = None
            series_game_recorded = False
            ui_state.game_requested = False

        if ui_state.series_requested:
            series = Series(
                length=ui_state.selected_series_length,
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
            )
            game = series.new_game()
            series_game_recorded = False
            ui_state.series_requested = False

        if ui_state.resume_requested:
            loaded = persistence.load_game()
            if loaded is None:
                ui_state.screen = Screen.SETTINGS
            else:
                game, series = loaded
            series_game_recorded = False
            ui_state.resume_requested = False

        if ui_state.next_game_requested:
            game = series.new_game()
            series_game_recorded = False
            ui_state.next_game_requested = False

        if series is not None and game is not None and game.state == TurnState.GAME_OVER and not series_game_recorded:
            series.record_game(game.winner())
            series_game_recorded = True

        if ui_state.screen == Screen.PLAYING:
            game_input.update_hover(game, ui_state)

        renderer.draw(game, ui_state, series)
        clock.tick(FPS)

    if persistence.has_game_in_progress(game):
        persistence.save_game(game, series)

    pygame.quit()
