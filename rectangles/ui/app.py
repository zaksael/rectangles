from __future__ import annotations

import pygame

from ..game import Game
from . import input as game_input
from . import layout
from .renderer import Renderer
from .state import UIState

FPS = 60


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Rectangles")
    screen = pygame.display.set_mode((layout.WINDOW_WIDTH, layout.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game = Game()
    ui_state = UIState()
    renderer = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if not game_input.handle_event(event, game, ui_state):
                running = False

        game_input.update_hover(game, ui_state)
        renderer.draw(game, ui_state)
        clock.tick(FPS)

    pygame.quit()
