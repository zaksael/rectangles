from __future__ import annotations

import pygame

from ..constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    FLAG_BONUS_POINTS_PRESETS,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
)

CELL_PX = 44

# The window is sized to fit the largest selectable board; a smaller chosen
# board simply renders smaller within that fixed, top-left-anchored area.
MAX_BOARD_SIZE = max(BOARD_SIZE_PRESETS)
BOARD_PX = MAX_BOARD_SIZE * CELL_PX
PANEL_WIDTH = 340
WINDOW_WIDTH = BOARD_PX + PANEL_WIDTH


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
    values: tuple[int | str, ...],
    y: int,
    center_x: int = WINDOW_WIDTH // 2,
    button_w: int = 90,
    button_h: int = 50,
    gap: int = 16,
) -> dict[int | str, pygame.Rect]:
    total_w = len(values) * button_w + (len(values) - 1) * gap
    start_x = center_x - total_w // 2
    return {
        value: pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)
        for i, value in enumerate(values)
    }


# Settings are grouped into three cards rather than one ever-taller vertical
# stack: "Board Setup" and "Opponent & Match" side by side on top (same
# height, so neither dwarfs the other), and a full-width "House Rules" card
# below holding every optional toggle (Doubles/Flag Conquest/Walls and any
# future ones), so new house rules grow that one card sideways/downward
# instead of making "Board Setup" taller and lopsided again.
SETTINGS_LEFT_COLUMN_X = WINDOW_WIDTH // 2 - 260
SETTINGS_RIGHT_COLUMN_X = WINDOW_WIDTH // 2 + 260

SETTINGS_BOARD_CARD_RECT = pygame.Rect(SETTINGS_LEFT_COLUMN_X - 240, 120, 480, 420)
SETTINGS_MATCH_CARD_RECT = pygame.Rect(SETTINGS_RIGHT_COLUMN_X - 240, 120, 480, 420)
SETTINGS_HOUSE_RULES_CARD_RECT = pygame.Rect(
    SETTINGS_BOARD_CARD_RECT.left,
    SETTINGS_BOARD_CARD_RECT.bottom + 30,
    SETTINGS_MATCH_CARD_RECT.right - SETTINGS_BOARD_CARD_RECT.left,
    270,
)

SETTINGS_BOARD_SIZE_BUTTON_RECTS = _centered_button_row(
    BOARD_SIZE_PRESETS, y=210, center_x=SETTINGS_LEFT_COLUMN_X
)
SETTINGS_SKIP_LIMIT_BUTTON_RECTS = _centered_button_row(
    SKIP_LIMIT_PRESETS, y=310, center_x=SETTINGS_LEFT_COLUMN_X
)

SETTINGS_BOT_BUTTON_RECT = pygame.Rect(SETTINGS_RIGHT_COLUMN_X - 80, 210, 160, 50)
SETTINGS_SERIES_LENGTH_BUTTON_RECTS = _centered_button_row(
    SERIES_LENGTH_PRESETS, y=310, center_x=SETTINGS_RIGHT_COLUMN_X, button_w=120
)
SETTINGS_BOT_DIFFICULTY_BUTTON_RECTS = _centered_button_row(
    BOT_DIFFICULTY_PRESETS, y=410, center_x=SETTINGS_RIGHT_COLUMN_X, button_w=120
)

# Three evenly-spaced toggle columns within the House Rules card, each with
# the same margin (87px) from its nearer card edge as from its neighbors.
SETTINGS_RULE_COLUMN_1_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width // 6
SETTINGS_RULE_COLUMN_2_X = SETTINGS_HOUSE_RULES_CARD_RECT.centerx
SETTINGS_RULE_COLUMN_3_X = SETTINGS_HOUSE_RULES_CARD_RECT.right - SETTINGS_HOUSE_RULES_CARD_RECT.width // 6

_RULE_TOGGLE_Y = SETTINGS_HOUSE_RULES_CARD_RECT.top + 100
SETTINGS_DOUBLES_BUTTON_RECT = pygame.Rect(SETTINGS_RULE_COLUMN_1_X - 80, _RULE_TOGGLE_Y, 160, 50)
SETTINGS_FLAG_CONQUEST_BUTTON_RECT = pygame.Rect(SETTINGS_RULE_COLUMN_2_X - 80, _RULE_TOGGLE_Y, 160, 50)
SETTINGS_WALLS_BUTTON_RECT = pygame.Rect(SETTINGS_RULE_COLUMN_3_X - 80, _RULE_TOGGLE_Y, 160, 50)
SETTINGS_FLAG_BONUS_BUTTON_RECTS = _centered_button_row(
    FLAG_BONUS_POINTS_PRESETS, y=SETTINGS_HOUSE_RULES_CARD_RECT.top + 200, center_x=SETTINGS_RULE_COLUMN_2_X
)

_SETTINGS_BUTTON_W = 200
_SETTINGS_BUTTON_H = 56
_SETTINGS_BUTTON_GAP = 20
# Derived from the House Rules card (the tallest/lowest of the three) rather
# than a hardcoded Y, so the two never overlap.
_SETTINGS_START_BUTTONS_Y = SETTINGS_HOUSE_RULES_CARD_RECT.bottom + 16
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

# The window is at least as tall as the largest board, but grows further if
# the settings screen's button stack needs more room than that (e.g. once the
# flag-conquest rows push the left card taller).
WINDOW_HEIGHT = max(BOARD_PX, SETTINGS_RESUME_BUTTON_RECT.bottom + 32)

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

# The history log's content never exceeds PANEL_HISTORY_MAX_ROWS, leaving a fixed idle
# gap before the footer divider - the series stats block (when a series is active) lives
# in that gap instead of needing its own dynamic layout.
PANEL_SERIES_DIVIDER_Y = 558
PANEL_SERIES_LABEL_Y = 572
PANEL_SERIES_START_Y = 596
PANEL_SERIES_ROW_HEIGHT = 20

# Mouse-wheel hit region for scrolling the history log - stops at the series stats
# section (when present) rather than the footer, so wheel input over that block doesn't
# scroll an unrelated section.
PANEL_HISTORY_REGION_RECT = pygame.Rect(
    PANEL_X, PANEL_HISTORY_START_Y, PANEL_CONTENT_WIDTH, PANEL_SERIES_DIVIDER_Y - PANEL_HISTORY_START_Y - 8
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
