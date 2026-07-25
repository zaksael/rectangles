from __future__ import annotations

import pygame

from .. import persistence
from ..game import Game
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
    ui_state = UIState()
    renderer = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if ui_state.screen == Screen.SETTINGS:
                if not game_input.handle_settings_event(event, ui_state):
                    running = False
            else:
                if not game_input.handle_event(event, game, ui_state):
                    running = False

        if ui_state.game_requested:
            game = Game(board_size=ui_state.selected_board_size, skip_limit=ui_state.selected_skip_limit)
            ui_state.game_requested = False

        if ui_state.resume_requested:
            game = persistence.load_game()
            if game is None:
                ui_state.screen = Screen.SETTINGS
            ui_state.resume_requested = False

        if ui_state.screen == Screen.PLAYING:
            game_input.update_hover(game, ui_state)

        renderer.draw(game, ui_state)
        clock.tick(FPS)

    if persistence.has_game_in_progress(game):
        persistence.save_game(game)

    pygame.quit()
