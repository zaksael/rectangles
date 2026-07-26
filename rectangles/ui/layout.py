from __future__ import annotations

import pygame

from ..constants import BOARD_SIZE_PRESETS, SERIES_LENGTH_PRESETS, SKIP_LIMIT_PRESETS

CELL_PX = 44

# The window is sized to fit the largest selectable board; a smaller chosen
# board simply renders smaller within that fixed, top-left-anchored area.
MAX_BOARD_SIZE = max(BOARD_SIZE_PRESETS)
BOARD_PX = MAX_BOARD_SIZE * CELL_PX
PANEL_WIDTH = 340
WINDOW_WIDTH = BOARD_PX + PANEL_WIDTH
WINDOW_HEIGHT = BOARD_PX

PANEL_RECT = pygame.Rect(BOARD_PX, 0, PANEL_WIDTH, WINDOW_HEIGHT)

PANEL_PADDING = 24
PANEL_X = BOARD_PX + PANEL_PADDING
PANEL_CONTENT_WIDTH = PANEL_WIDTH - 2 * PANEL_PADDING

# The panel is laid out as fixed vertical sections (header / scoreboard /
# status / action button / footer), each given a generous, hand-measured
# height budget so no state's text can ever grow into the next section's
# button - avoids needing a dynamic/reflowing layout for this small, fixed
# window.
PANEL_HEADER_Y = 28
PANEL_DIVIDER_1_Y = 82

PANEL_SCORE_Y = 104
PANEL_SCORE_ROW_HEIGHT = 34
PANEL_DIVIDER_2_Y = 192

PANEL_STATUS_Y = 216
PANEL_ACTION_BUTTON_Y = 300

ROLL_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, PANEL_CONTENT_WIDTH, 56)
CONTINUE_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, PANEL_CONTENT_WIDTH, 56)
ROTATE_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, 160, 40)

# Turn-history log fills the gap between the action button and the footer.
PANEL_HISTORY_DIVIDER_Y = 372
PANEL_HISTORY_LABEL_Y = 386
PANEL_HISTORY_START_Y = 412
PANEL_HISTORY_ROW_HEIGHT = 22
PANEL_HISTORY_MAX_ROWS = 6

PANEL_FOOTER_DIVIDER_Y = WINDOW_HEIGHT - 144

SURRENDER_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_FOOTER_DIVIDER_Y + 16, PANEL_CONTENT_WIDTH, 40)

_FOOTER_BUTTON_GAP = 12
_FOOTER_BUTTON_W = (PANEL_CONTENT_WIDTH - _FOOTER_BUTTON_GAP) // 2
_FOOTER_BUTTON_Y = WINDOW_HEIGHT - 76

NEW_GAME_BUTTON_RECT = pygame.Rect(PANEL_X, _FOOTER_BUTTON_Y, _FOOTER_BUTTON_W, 44)
EXIT_BUTTON_RECT = pygame.Rect(
    PANEL_X + _FOOTER_BUTTON_W + _FOOTER_BUTTON_GAP, _FOOTER_BUTTON_Y, _FOOTER_BUTTON_W, 44
)

# Mouse-wheel hit region for scrolling the history log.
PANEL_HISTORY_REGION_RECT = pygame.Rect(
    PANEL_X, PANEL_HISTORY_START_Y, PANEL_CONTENT_WIDTH, PANEL_FOOTER_DIVIDER_Y - PANEL_HISTORY_START_Y - 8
)

_CONFIRM_DIALOG_WIDTH = 420
_CONFIRM_DIALOG_HEIGHT = 170
CONFIRM_DIALOG_RECT = pygame.Rect(
    (WINDOW_WIDTH - _CONFIRM_DIALOG_WIDTH) // 2,
    (WINDOW_HEIGHT - _CONFIRM_DIALOG_HEIGHT) // 2,
    _CONFIRM_DIALOG_WIDTH,
    _CONFIRM_DIALOG_HEIGHT,
)

_CONFIRM_BUTTON_W = 140
_CONFIRM_BUTTON_H = 48
_CONFIRM_BUTTON_GAP = 20
_CONFIRM_BUTTONS_Y = CONFIRM_DIALOG_RECT.bottom - 64
_CONFIRM_BUTTONS_START_X = (WINDOW_WIDTH - (2 * _CONFIRM_BUTTON_W + _CONFIRM_BUTTON_GAP)) // 2

CONFIRM_YES_BUTTON_RECT = pygame.Rect(
    _CONFIRM_BUTTONS_START_X, _CONFIRM_BUTTONS_Y, _CONFIRM_BUTTON_W, _CONFIRM_BUTTON_H
)
CONFIRM_NO_BUTTON_RECT = pygame.Rect(
    _CONFIRM_BUTTONS_START_X + _CONFIRM_BUTTON_W + _CONFIRM_BUTTON_GAP,
    _CONFIRM_BUTTONS_Y,
    _CONFIRM_BUTTON_W,
    _CONFIRM_BUTTON_H,
)


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


SETTINGS_BOARD_SIZE_BUTTON_RECTS = _centered_button_row(BOARD_SIZE_PRESETS, y=178)
SETTINGS_SKIP_LIMIT_BUTTON_RECTS = _centered_button_row(SKIP_LIMIT_PRESETS, y=292)
SETTINGS_SERIES_LENGTH_BUTTON_RECTS = _centered_button_row(SERIES_LENGTH_PRESETS, y=406)

# Sits beside the skip-limit row (same y) rather than its own row, since the
# settings screen is already vertically tight but has unused horizontal room.
SETTINGS_DOUBLES_BUTTON_RECT = pygame.Rect(
    SETTINGS_SKIP_LIMIT_BUTTON_RECTS[max(SKIP_LIMIT_PRESETS)].right + 40, 292, 160, 50
)

# Sits beside the series-length row the same way the doubles toggle sits
# beside skip limit.
SETTINGS_BOT_BUTTON_RECT = pygame.Rect(
    SETTINGS_SERIES_LENGTH_BUTTON_RECTS[max(SERIES_LENGTH_PRESETS)].right + 40, 406, 160, 50
)

_SETTINGS_BUTTON_W = 200
_SETTINGS_BUTTON_H = 56
_SETTINGS_BUTTON_GAP = 20
_SETTINGS_START_BUTTONS_Y = 496
_SETTINGS_BUTTONS_START_X = (
    WINDOW_WIDTH - (2 * _SETTINGS_BUTTON_W + _SETTINGS_BUTTON_GAP)
) // 2

SETTINGS_START_BUTTON_RECT = pygame.Rect(
    _SETTINGS_BUTTONS_START_X, _SETTINGS_START_BUTTONS_Y, _SETTINGS_BUTTON_W, _SETTINGS_BUTTON_H
)
SETTINGS_START_SERIES_BUTTON_RECT = pygame.Rect(
    _SETTINGS_BUTTONS_START_X + _SETTINGS_BUTTON_W + _SETTINGS_BUTTON_GAP,
    _SETTINGS_START_BUTTONS_Y,
    _SETTINGS_BUTTON_W,
    _SETTINGS_BUTTON_H,
)

# Exit / Resume sit in their own centered rows below the Start Game / Start
# Series row, each slightly shorter so all three rows fit under WINDOW_HEIGHT.
_SETTINGS_SECONDARY_BUTTON_H = 48

_SETTINGS_EXIT_BUTTON_Y = _SETTINGS_START_BUTTONS_Y + _SETTINGS_BUTTON_H + 16
SETTINGS_EXIT_BUTTON_RECT = pygame.Rect(
    (WINDOW_WIDTH - _SETTINGS_BUTTON_W) // 2,
    _SETTINGS_EXIT_BUTTON_Y,
    _SETTINGS_BUTTON_W,
    _SETTINGS_SECONDARY_BUTTON_H,
)

_SETTINGS_RESUME_BUTTON_Y = _SETTINGS_EXIT_BUTTON_Y + _SETTINGS_SECONDARY_BUTTON_H + 12
SETTINGS_RESUME_BUTTON_RECT = pygame.Rect(
    (WINDOW_WIDTH - _SETTINGS_BUTTON_W) // 2,
    _SETTINGS_RESUME_BUTTON_Y,
    _SETTINGS_BUTTON_W,
    _SETTINGS_SECONDARY_BUTTON_H,
)

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
