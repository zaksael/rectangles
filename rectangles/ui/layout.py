from __future__ import annotations

import pygame

from ..constants import BOARD_SIZE_PRESETS, SKIP_LIMIT_PRESETS

CELL_PX = 44

# The window is sized to fit the largest selectable board; a smaller chosen
# board simply renders smaller within that fixed, top-left-anchored area.
MAX_BOARD_SIZE = max(BOARD_SIZE_PRESETS)
BOARD_PX = MAX_BOARD_SIZE * CELL_PX
PANEL_WIDTH = 300
WINDOW_WIDTH = BOARD_PX + PANEL_WIDTH
WINDOW_HEIGHT = BOARD_PX

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


def board_rect(board_size: int) -> pygame.Rect:
    return pygame.Rect(0, 0, board_size * CELL_PX, board_size * CELL_PX)


def pixel_to_cell(x: int, y: int, board_size: int) -> tuple[int, int] | None:
    if not board_rect(board_size).collidepoint(x, y):
        return None
    return (y // CELL_PX, x // CELL_PX)


def _centered_button_row(
    values: tuple[int, ...], y: int, button_w: int = 90, button_h: int = 50, gap: int = 16
) -> dict[int, pygame.Rect]:
    total_w = len(values) * button_w + (len(values) - 1) * gap
    start_x = (WINDOW_WIDTH - total_w) // 2
    return {
        value: pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)
        for i, value in enumerate(values)
    }


SETTINGS_BOARD_SIZE_BUTTON_RECTS = _centered_button_row(BOARD_SIZE_PRESETS, y=260)
SETTINGS_SKIP_LIMIT_BUTTON_RECTS = _centered_button_row(SKIP_LIMIT_PRESETS, y=400)
SETTINGS_START_BUTTON_RECT = pygame.Rect((WINDOW_WIDTH - 240) // 2, 500, 240, 56)

_GAME_OVER_BUTTON_W = 150
_GAME_OVER_BUTTON_H = 48
_GAME_OVER_BUTTON_GAP = 20
_GAME_OVER_BUTTONS_Y = WINDOW_HEIGHT // 2 + 80
_GAME_OVER_BUTTONS_START_X = (WINDOW_WIDTH - (2 * _GAME_OVER_BUTTON_W + _GAME_OVER_BUTTON_GAP)) // 2

GAME_OVER_NEW_GAME_BUTTON_RECT = pygame.Rect(
    _GAME_OVER_BUTTONS_START_X, _GAME_OVER_BUTTONS_Y, _GAME_OVER_BUTTON_W, _GAME_OVER_BUTTON_H
)
GAME_OVER_EXIT_BUTTON_RECT = pygame.Rect(
    _GAME_OVER_BUTTONS_START_X + _GAME_OVER_BUTTON_W + _GAME_OVER_BUTTON_GAP,
    _GAME_OVER_BUTTONS_Y,
    _GAME_OVER_BUTTON_W,
    _GAME_OVER_BUTTON_H,
)
