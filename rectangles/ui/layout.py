from __future__ import annotations

import pygame

from ..constants import BOARD_SIZE

CELL_PX = 44
BOARD_PX = BOARD_SIZE * CELL_PX
PANEL_WIDTH = 300
WINDOW_WIDTH = BOARD_PX + PANEL_WIDTH
WINDOW_HEIGHT = BOARD_PX

BOARD_RECT = pygame.Rect(0, 0, BOARD_PX, BOARD_PX)
PANEL_RECT = pygame.Rect(BOARD_PX, 0, PANEL_WIDTH, WINDOW_HEIGHT)

PANEL_PADDING = 20
PANEL_X = BOARD_PX + PANEL_PADDING
PANEL_CONTENT_WIDTH = PANEL_WIDTH - 2 * PANEL_PADDING

ROLL_BUTTON_RECT = pygame.Rect(PANEL_X, 160, PANEL_CONTENT_WIDTH, 44)
CONTINUE_BUTTON_RECT = pygame.Rect(PANEL_X, 160, PANEL_CONTENT_WIDTH, 44)
ROTATE_BUTTON_RECT = pygame.Rect(PANEL_X, 220, PANEL_CONTENT_WIDTH, 40)
NEW_GAME_BUTTON_RECT = pygame.Rect(PANEL_X, WINDOW_HEIGHT - 56, PANEL_CONTENT_WIDTH, 40)


def cell_rect(r: int, c: int) -> pygame.Rect:
    return pygame.Rect(c * CELL_PX, r * CELL_PX, CELL_PX, CELL_PX)


def piece_rect(top_left: tuple[int, int], w: int, h: int) -> pygame.Rect:
    r, c = top_left
    return pygame.Rect(c * CELL_PX, r * CELL_PX, w * CELL_PX, h * CELL_PX)


def pixel_to_cell(x: int, y: int) -> tuple[int, int] | None:
    if not BOARD_RECT.collidepoint(x, y):
        return None
    return (y // CELL_PX, x // CELL_PX)
