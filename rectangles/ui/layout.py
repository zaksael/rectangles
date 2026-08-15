from __future__ import annotations

import pygame

from ..constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    DICE_MAX,
    DICE_MIN,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
)

CELL_PX = 44

# A board's on-screen footprint is capped at TARGET_BOARD_PX (today's
# 19 * 44) regardless of board_size, so BOARD_PX/WINDOW_WIDTH stay fixed even
# if BOARD_SIZE_PRESETS grows to include a bigger tier later - only cell_px()
# shrinks to make a larger board still fit that same footprint.
TARGET_BOARD_PX = 836
MAX_BOARD_SIZE = max(BOARD_SIZE_PRESETS)
BOARD_PX = TARGET_BOARD_PX
PANEL_WIDTH = 340
WINDOW_WIDTH = BOARD_PX + PANEL_WIDTH


def cell_px(board_size: int) -> int:
    return min(CELL_PX, TARGET_BOARD_PX // board_size)


def cell_rect(r: int, c: int, board_size: int) -> pygame.Rect:
    px = cell_px(board_size)
    return pygame.Rect(c * px, r * px, px, px)


def piece_rect(top_left: tuple[int, int], w: int, h: int, board_size: int) -> pygame.Rect:
    r, c = top_left
    px = cell_px(board_size)
    return pygame.Rect(c * px, r * px, w * px, h * px)


def board_rect(board_size: int) -> pygame.Rect:
    px = cell_px(board_size)
    return pygame.Rect(0, 0, board_size * px, board_size * px)


def pixel_to_cell(x: int, y: int, board_size: int) -> tuple[int, int] | None:
    if not board_rect(board_size).collidepoint(x, y):
        return None
    px = cell_px(board_size)
    return (y // px, x // px)


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
# below holding every optional toggle (Flag Conquest/Walls/Wildcard Roll and
# any future ones), so new house rules grow that one card sideways/downward
# instead of making "Board Setup" taller and lopsided again.
SETTINGS_LEFT_COLUMN_X = WINDOW_WIDTH // 2 - 260
SETTINGS_RIGHT_COLUMN_X = WINDOW_WIDTH // 2 + 260

SETTINGS_BOARD_CARD_RECT = pygame.Rect(SETTINGS_LEFT_COLUMN_X - 240, 120, 480, 330)
SETTINGS_MATCH_CARD_RECT = pygame.Rect(SETTINGS_RIGHT_COLUMN_X - 240, 120, 480, 330)
SETTINGS_HOUSE_RULES_CARD_RECT = pygame.Rect(
    SETTINGS_BOARD_CARD_RECT.left,
    SETTINGS_BOARD_CARD_RECT.bottom + 20,
    SETTINGS_MATCH_CARD_RECT.right - SETTINGS_BOARD_CARD_RECT.left,
    220,
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
    BOT_DIFFICULTY_PRESETS, y=395, center_x=SETTINGS_RIGHT_COLUMN_X, button_w=120
)

# Four evenly-spaced toggle columns within the House Rules card - each column
# centered in its own quarter of the card's width, so the same margin
# separates every button from its neighbors and from the card edges.
SETTINGS_RULE_COLUMN_1_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 1 // 8
SETTINGS_RULE_COLUMN_2_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 3 // 8
SETTINGS_RULE_COLUMN_3_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 5 // 8
SETTINGS_RULE_COLUMN_4_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 7 // 8

_RULE_TOGGLE_Y = SETTINGS_HOUSE_RULES_CARD_RECT.top + 100
_RULE_BUTTON_W = 140
SETTINGS_FLAG_CONQUEST_BUTTON_RECT = pygame.Rect(
    SETTINGS_RULE_COLUMN_1_X - _RULE_BUTTON_W // 2, _RULE_TOGGLE_Y, _RULE_BUTTON_W, 50
)
SETTINGS_WALLS_BUTTON_RECT = pygame.Rect(
    SETTINGS_RULE_COLUMN_2_X - _RULE_BUTTON_W // 2, _RULE_TOGGLE_Y, _RULE_BUTTON_W, 50
)
SETTINGS_OBSTACLES_BUTTON_RECT = pygame.Rect(
    SETTINGS_RULE_COLUMN_3_X - _RULE_BUTTON_W // 2, _RULE_TOGGLE_Y, _RULE_BUTTON_W, 50
)
SETTINGS_WILDCARD_BUTTON_RECT = pygame.Rect(
    SETTINGS_RULE_COLUMN_4_X - _RULE_BUTTON_W // 2, _RULE_TOGGLE_Y, _RULE_BUTTON_W, 50
)

SETTINGS_ALL_RULES_BUTTON_RECT = pygame.Rect(
    SETTINGS_HOUSE_RULES_CARD_RECT.centerx - 100, SETTINGS_HOUSE_RULES_CARD_RECT.top + 160, 200, 40
)

_SETTINGS_BUTTON_W = 200
_SETTINGS_BUTTON_H = 56
_SETTINGS_BUTTON_GAP = 20
# Derived from the House Rules card (the tallest/lowest of the three) rather
# than a hardcoded Y, so the two never overlap.
_SETTINGS_START_BUTTONS_Y = SETTINGS_HOUSE_RULES_CARD_RECT.bottom + 12
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

# Exit / Resume share one centered row below Start Game / Start Series
# (mirroring that row's side-by-side layout) rather than two stacked rows -
# Resume is only ever drawn/clickable when a save exists (see
# persistence.has_save()), but Exit stays put in its left slot either way.
_SETTINGS_SECONDARY_BUTTON_H = 48
_SETTINGS_SECONDARY_BUTTONS_Y = _SETTINGS_START_BUTTONS_Y + _SETTINGS_BUTTON_H + 12

SETTINGS_EXIT_BUTTON_RECT = pygame.Rect(
    _SETTINGS_BUTTONS_START_X, _SETTINGS_SECONDARY_BUTTONS_Y, _SETTINGS_BUTTON_W, _SETTINGS_SECONDARY_BUTTON_H
)
SETTINGS_RESUME_BUTTON_RECT = pygame.Rect(
    _SETTINGS_BUTTONS_START_X + _SETTINGS_BUTTON_W + _SETTINGS_BUTTON_GAP,
    _SETTINGS_SECONDARY_BUTTONS_Y,
    _SETTINGS_BUTTON_W,
    _SETTINGS_SECONDARY_BUTTON_H,
)

# The settings screen's own full button stack, top to bottom - independent of
# the actual window height. When it's taller than the actual window, the
# settings screen scrolls (see settings_max_scroll() and
# Renderer._settings_surface) rather than growing the window to fit, so
# adding another settings row never risks pushing the window past what a
# small display can show.
SETTINGS_CONTENT_HEIGHT = SETTINGS_RESUME_BUTTON_RECT.bottom + 20


def settings_max_scroll(window_height: int) -> int:
    return max(0, SETTINGS_CONTENT_HEIGHT - window_height)


# The window is resizable (see ui/app.py); width is pinned at WINDOW_WIDTH
# (every board/settings/panel column position assumes it), only height
# flexes. Every panel constant below that depends on the window's bottom
# edge (the footer + everything under it) reads live window height as a
# parameter instead of baking in a fixed constant, precisely so shrinking
# the window doesn't clip them - EXCEPT the history and (capped, see
# PANEL_SERIES_MAX_ROWS below) series-stats blocks below the roll button,
# which are fixed-from-the-top positions like the rest of that section, so
# they don't reflow. MIN_WINDOW_HEIGHT is therefore a real floor, not just a
# nicety: it's the smallest height at which the footer (top = window_height
# - 144) still clears the worst case those two fixed blocks can reach - a
# maxed-out history log plus a capped series-stats table both showing,
# bottom ~696 (PANEL_SERIES_START_Y=596 + PANEL_SERIES_MAX_ROWS(5)*
# PANEL_SERIES_ROW_HEIGHT(20)) - with a bit of margin. WINDOW_HEIGHT (the
# initial/default size) is never below this floor either.
MIN_WINDOW_HEIGHT = 860
WINDOW_HEIGHT = max(BOARD_PX, MIN_WINDOW_HEIGHT)

PANEL_PADDING = 24
PANEL_X = BOARD_PX + PANEL_PADDING
PANEL_CONTENT_WIDTH = PANEL_WIDTH - 2 * PANEL_PADDING


def panel_rect(window_height: int) -> pygame.Rect:
    return pygame.Rect(BOARD_PX, 0, PANEL_WIDTH, window_height)


# The panel is laid out as fixed vertical sections (header / scoreboard /
# status / action button / footer), each given a generous, hand-measured
# height budget so no state's text can ever grow into the next section's
# button - avoids needing a dynamic/reflowing layout for the top section.
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

# 2 rows x 3 columns: the 72px gap before PANEL_HISTORY_DIVIDER_Y only fits
# two rows at a shrunk 32px button height (32*2 + 6px row gap = 70px).
_WILDCARD_BUTTON_W = 40
_WILDCARD_BUTTON_H = 32
_WILDCARD_BUTTON_GAP = 8
_WILDCARD_ROW_GAP = 6
_WILDCARD_COLS = 3
_wildcard_row_width = _WILDCARD_COLS * _WILDCARD_BUTTON_W + (_WILDCARD_COLS - 1) * _WILDCARD_BUTTON_GAP
_WILDCARD_ROW_X = PANEL_X + (PANEL_CONTENT_WIDTH - _wildcard_row_width) // 2
WILDCARD_VALUE_BUTTON_RECTS = {
    value: pygame.Rect(
        _WILDCARD_ROW_X + (i % _WILDCARD_COLS) * (_WILDCARD_BUTTON_W + _WILDCARD_BUTTON_GAP),
        PANEL_ACTION_BUTTON_Y + (i // _WILDCARD_COLS) * (_WILDCARD_BUTTON_H + _WILDCARD_ROW_GAP),
        _WILDCARD_BUTTON_W,
        _WILDCARD_BUTTON_H,
    )
    for i, value in enumerate(range(DICE_MIN, DICE_MAX + 1))
}

# Turn-history log fills the gap between the action button and the footer.
PANEL_HISTORY_DIVIDER_Y = 372
PANEL_HISTORY_LABEL_Y = 386
PANEL_HISTORY_START_Y = 412
PANEL_HISTORY_ROW_HEIGHT = 22
PANEL_HISTORY_MAX_ROWS = 6

# The footer (divider + Surrender/New Game/Exit) anchors to the bottom of the
# *actual* window rather than a fixed offset from the top, so it tracks a
# live resize instead of drifting into (or leaving a gap above) the content
# above it.
def panel_footer_divider_y(window_height: int) -> int:
    return window_height - 144


def surrender_button_rect(window_height: int) -> pygame.Rect:
    return pygame.Rect(PANEL_X, panel_footer_divider_y(window_height) + 16, PANEL_CONTENT_WIDTH, 40)


_FOOTER_BUTTON_GAP = 12
_FOOTER_BUTTON_W = (PANEL_CONTENT_WIDTH - _FOOTER_BUTTON_GAP) // 2


def new_game_button_rect(window_height: int) -> pygame.Rect:
    return pygame.Rect(PANEL_X, window_height - 76, _FOOTER_BUTTON_W, 44)


def exit_button_rect(window_height: int) -> pygame.Rect:
    return pygame.Rect(
        PANEL_X + _FOOTER_BUTTON_W + _FOOTER_BUTTON_GAP, window_height - 76, _FOOTER_BUTTON_W, 44
    )


# The history log's content never exceeds PANEL_HISTORY_MAX_ROWS, leaving a fixed idle
# gap before the footer divider - the series stats block (when a series is active) lives
# in that gap instead of needing its own dynamic layout. PANEL_SERIES_MAX_ROWS caps that
# block the same way (header + up to this many more lines, truncating older rounds behind
# a "N earlier" note - see Renderer._draw_series_stats) so its height stays bounded
# regardless of series length, which matters now that the footer above can be much
# closer than it used to be on a shrunk window.
PANEL_SERIES_DIVIDER_Y = 558
PANEL_SERIES_LABEL_Y = 572
PANEL_SERIES_START_Y = 596
PANEL_SERIES_ROW_HEIGHT = 20
PANEL_SERIES_MAX_ROWS = 5

# Mouse-wheel hit region for scrolling the history log - stops at the series stats
# section (when present) rather than the footer, so wheel input over that block doesn't
# scroll an unrelated section.
PANEL_HISTORY_REGION_RECT = pygame.Rect(
    PANEL_X, PANEL_HISTORY_START_Y, PANEL_CONTENT_WIDTH, PANEL_SERIES_DIVIDER_Y - PANEL_HISTORY_START_Y - 8
)

_CONFIRM_DIALOG_WIDTH = 420
_CONFIRM_DIALOG_HEIGHT = 170


def confirm_dialog_rect(window_width: int, window_height: int) -> pygame.Rect:
    return pygame.Rect(
        (window_width - _CONFIRM_DIALOG_WIDTH) // 2,
        (window_height - _CONFIRM_DIALOG_HEIGHT) // 2,
        _CONFIRM_DIALOG_WIDTH,
        _CONFIRM_DIALOG_HEIGHT,
    )


_CONFIRM_BUTTON_W = 140
_CONFIRM_BUTTON_H = 48
_CONFIRM_BUTTON_GAP = 20


def _confirm_buttons_origin(window_width: int, window_height: int) -> tuple[int, int]:
    y = confirm_dialog_rect(window_width, window_height).bottom - 64
    x = (window_width - (2 * _CONFIRM_BUTTON_W + _CONFIRM_BUTTON_GAP)) // 2
    return x, y


def confirm_yes_button_rect(window_width: int, window_height: int) -> pygame.Rect:
    x, y = _confirm_buttons_origin(window_width, window_height)
    return pygame.Rect(x, y, _CONFIRM_BUTTON_W, _CONFIRM_BUTTON_H)


def confirm_no_button_rect(window_width: int, window_height: int) -> pygame.Rect:
    x, y = _confirm_buttons_origin(window_width, window_height)
    return pygame.Rect(x + _CONFIRM_BUTTON_W + _CONFIRM_BUTTON_GAP, y, _CONFIRM_BUTTON_W, _CONFIRM_BUTTON_H)


_GAME_OVER_BUTTON_W = 150
_GAME_OVER_BUTTON_H = 48
_GAME_OVER_BUTTON_GAP = 20


def _game_over_buttons_origin(window_width: int, window_height: int) -> tuple[int, int]:
    y = window_height // 2 + 80
    x = (window_width - (3 * _GAME_OVER_BUTTON_W + 2 * _GAME_OVER_BUTTON_GAP)) // 2
    return x, y


def game_over_new_game_button_rect(window_width: int, window_height: int) -> pygame.Rect:
    x, y = _game_over_buttons_origin(window_width, window_height)
    return pygame.Rect(x, y, _GAME_OVER_BUTTON_W, _GAME_OVER_BUTTON_H)


def game_over_replay_button_rect(window_width: int, window_height: int) -> pygame.Rect:
    x, y = _game_over_buttons_origin(window_width, window_height)
    return pygame.Rect(
        x + _GAME_OVER_BUTTON_W + _GAME_OVER_BUTTON_GAP, y, _GAME_OVER_BUTTON_W, _GAME_OVER_BUTTON_H
    )


def game_over_exit_button_rect(window_width: int, window_height: int) -> pygame.Rect:
    x, y = _game_over_buttons_origin(window_width, window_height)
    return pygame.Rect(
        x + 2 * (_GAME_OVER_BUTTON_W + _GAME_OVER_BUTTON_GAP), y, _GAME_OVER_BUTTON_W, _GAME_OVER_BUTTON_H
    )


_REPLAY_BUTTON_W = 110
_REPLAY_BUTTON_H = 44
_REPLAY_BUTTON_GAP = 12
_REPLAY_BUTTON_Y_OFFSET = 76


def replay_button_rects(window_width: int, window_height: int) -> dict[str, pygame.Rect]:
    y = window_height - _REPLAY_BUTTON_Y_OFFSET
    return _centered_button_row(
        ("first", "prev", "next", "last", "back"),
        y,
        center_x=window_width // 2,
        button_w=_REPLAY_BUTTON_W,
        button_h=_REPLAY_BUTTON_H,
        gap=_REPLAY_BUTTON_GAP,
    )
