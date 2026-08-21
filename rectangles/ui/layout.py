from __future__ import annotations

import pygame

from ..constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    DICE_MAX,
    DICE_MIN,
    REPLAY_SPEED_PRESETS,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
    TOURNAMENT_SIZE_PRESETS,
)

CELL_PX = 44

# A board's on-screen footprint is capped at TARGET_BOARD_PX (today's
# 19 * 44) regardless of board_size, so BOARD_PX/DESIGN_WIDTH stay fixed even
# if BOARD_SIZE_PRESETS grows to include a bigger tier later - only cell_px()
# shrinks to make a larger board still fit that same footprint.
TARGET_BOARD_PX = 836
MAX_BOARD_SIZE = max(BOARD_SIZE_PRESETS)
BOARD_PX = TARGET_BOARD_PX
PANEL_WIDTH = 340

# Everything below is drawn onto one fixed-size virtual canvas at this design
# resolution; the finished canvas is then uniformly scaled (see
# compute_scale()) to fit the real, freely-resizable window - so nothing
# past this point ever needs to know the real window size. DESIGN_HEIGHT is
# sized to comfortably fit the panel's worst-case content (a maxed-out
# history log plus a capped series-stats table both showing, bottom ~720px -
# see PANEL_SERIES_MAX_ROWS/PANEL_HISTORY_MAX_ROWS below) with margin, and
# never below the board's own footprint either. Every fixed Y constant from
# PANEL_DIVIDER_2_Y down, plus DESIGN_HEIGHT itself, sits 24px lower than it
# used to (884, not 860) to make room for each score row's second line - see
# PANEL_SCORE_ROW_HEIGHT below.
DESIGN_WIDTH = BOARD_PX + PANEL_WIDTH
DESIGN_HEIGHT = max(BOARD_PX, 884)

# The real OS window can't shrink below this - a usability floor only (so it
# can't be dragged to something with no visible content), not a layout
# constraint; scaling handles any real size above it gracefully.
MIN_REAL_WINDOW_WIDTH = 480
MIN_REAL_WINDOW_HEIGHT = 360

# Clamp how far the canvas can be scaled up: past ~3x a design pixel looks
# visibly blurry. No lower clamp - MIN_REAL_WINDOW_WIDTH/HEIGHT above already
# keep the real window (and therefore this scale) from going small enough to
# need one, so a second floor here would just be dead code.
_MAX_SCALE = 3.0


def compute_scale(real_width: int, real_height: int) -> tuple[float, int, int]:
    """Uniform scale + centering offset to fit the DESIGN_WIDTH x
    DESIGN_HEIGHT canvas into a real_width x real_height window, preserving
    aspect ratio (board cells must stay square) - any leftover space becomes
    letterbox/pillarbox bars rather than stretching the canvas unevenly."""
    scale = min(real_width / DESIGN_WIDTH, real_height / DESIGN_HEIGHT)
    scale = min(_MAX_SCALE, scale)
    offset_x = (real_width - round(DESIGN_WIDTH * scale)) // 2
    offset_y = (real_height - round(DESIGN_HEIGHT * scale)) // 2
    return scale, offset_x, offset_y


def to_design_coords(real_x: int, real_y: int, real_width: int, real_height: int) -> tuple[int, int]:
    """Inverse of compute_scale: maps a real-window pixel (e.g. a mouse
    position) back to the fixed design canvas' coordinate space, the space
    every rect in this module is defined in. Shared by renderer.py (hover/
    cursor checks) and input.py (click/scroll hit-testing) - the one place
    this transform happens, rather than duplicated at each call site."""
    scale, offset_x, offset_y = compute_scale(real_width, real_height)
    return (round((real_x - offset_x) / scale), round((real_y - offset_y) / scale))


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
    center_x: int = DESIGN_WIDTH // 2,
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
SETTINGS_LEFT_COLUMN_X = DESIGN_WIDTH // 2 - 260
SETTINGS_RIGHT_COLUMN_X = DESIGN_WIDTH // 2 + 260

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

# Six evenly-spaced toggle columns within the House Rules card - each column
# centered in its own sixth of the card's width, so the same margin
# separates every button from its neighbors and from the card edges.
SETTINGS_RULE_COLUMN_1_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 1 // 12
SETTINGS_RULE_COLUMN_2_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 3 // 12
SETTINGS_RULE_COLUMN_3_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 5 // 12
SETTINGS_RULE_COLUMN_4_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 7 // 12
SETTINGS_RULE_COLUMN_5_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 9 // 12
SETTINGS_RULE_COLUMN_6_X = SETTINGS_HOUSE_RULES_CARD_RECT.left + SETTINGS_HOUSE_RULES_CARD_RECT.width * 11 // 12

_RULE_TOGGLE_Y = SETTINGS_HOUSE_RULES_CARD_RECT.top + 100
_RULE_BUTTON_W = 120
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
SETTINGS_SELF_ENCLOSED_PENALTY_BUTTON_RECT = pygame.Rect(
    SETTINGS_RULE_COLUMN_5_X - _RULE_BUTTON_W // 2, _RULE_TOGGLE_Y, _RULE_BUTTON_W, 50
)
SETTINGS_REROLL_BUTTON_RECT = pygame.Rect(
    SETTINGS_RULE_COLUMN_6_X - _RULE_BUTTON_W // 2, _RULE_TOGGLE_Y, _RULE_BUTTON_W, 50
)

SETTINGS_ALL_RULES_BUTTON_RECT = pygame.Rect(
    SETTINGS_HOUSE_RULES_CARD_RECT.centerx - 100, SETTINGS_HOUSE_RULES_CARD_RECT.top + 160, 200, 40
)

# Tournament card: a 4th, self-contained card below House Rules, with its own
# "Start Tournament" button at its own bottom (not squeezed into the shared
# Start Game/Start Series row below, which stays untouched at 2 buttons).
# Sized for TOURNAMENT_MAX_SLOTS rows regardless of the currently selected
# preset, so switching between 4 and 8 slots never resizes the card - unused
# rows (beyond the selected size) simply aren't drawn/clickable.
TOURNAMENT_MAX_SLOTS = max(TOURNAMENT_SIZE_PRESETS)
_TOURNAMENT_SLOT_ROW_H = 40
_TOURNAMENT_HEADER_H = 140  # card header text + "Tournament size" label + size-preset row
_TOURNAMENT_START_BUTTON_H = 48
SETTINGS_TOURNAMENT_CARD_RECT = pygame.Rect(
    SETTINGS_BOARD_CARD_RECT.left,
    SETTINGS_HOUSE_RULES_CARD_RECT.bottom + 20,
    SETTINGS_MATCH_CARD_RECT.right - SETTINGS_BOARD_CARD_RECT.left,
    _TOURNAMENT_HEADER_H + TOURNAMENT_MAX_SLOTS * _TOURNAMENT_SLOT_ROW_H + _TOURNAMENT_START_BUTTON_H + 20,
)

SETTINGS_TOURNAMENT_SIZE_BUTTON_RECTS = _centered_button_row(
    TOURNAMENT_SIZE_PRESETS, y=SETTINGS_TOURNAMENT_CARD_RECT.top + 90, button_w=90
)

_TOURNAMENT_SLOTS_START_Y = SETTINGS_TOURNAMENT_CARD_RECT.top + _TOURNAMENT_HEADER_H
SETTINGS_TOURNAMENT_SLOT_LABEL_X = SETTINGS_TOURNAMENT_CARD_RECT.left + 32
_TOURNAMENT_SLOT_TOGGLE_X = SETTINGS_TOURNAMENT_CARD_RECT.left + 160
_TOURNAMENT_SLOT_TOGGLE_W = 100
_TOURNAMENT_SLOT_DIFFICULTY_X = _TOURNAMENT_SLOT_TOGGLE_X + _TOURNAMENT_SLOT_TOGGLE_W + 20
_TOURNAMENT_SLOT_DIFFICULTY_BUTTON_W = 78
_TOURNAMENT_SLOT_DIFFICULTY_GAP = 8


def _tournament_slot_row_y(slot: int) -> int:
    return _TOURNAMENT_SLOTS_START_Y + slot * _TOURNAMENT_SLOT_ROW_H


SETTINGS_TOURNAMENT_SLOT_TOGGLE_RECTS = [
    pygame.Rect(_TOURNAMENT_SLOT_TOGGLE_X, _tournament_slot_row_y(i), _TOURNAMENT_SLOT_TOGGLE_W, 32)
    for i in range(TOURNAMENT_MAX_SLOTS)
]
SETTINGS_TOURNAMENT_SLOT_DIFFICULTY_RECTS = [
    {
        value: pygame.Rect(
            _TOURNAMENT_SLOT_DIFFICULTY_X + j * (_TOURNAMENT_SLOT_DIFFICULTY_BUTTON_W + _TOURNAMENT_SLOT_DIFFICULTY_GAP),
            _tournament_slot_row_y(i),
            _TOURNAMENT_SLOT_DIFFICULTY_BUTTON_W,
            32,
        )
        for j, value in enumerate(BOT_DIFFICULTY_PRESETS)
    }
    for i in range(TOURNAMENT_MAX_SLOTS)
]

SETTINGS_START_TOURNAMENT_BUTTON_RECT = pygame.Rect(
    SETTINGS_TOURNAMENT_CARD_RECT.centerx - 110,
    SETTINGS_TOURNAMENT_CARD_RECT.bottom - _TOURNAMENT_START_BUTTON_H - 16,
    220,
    _TOURNAMENT_START_BUTTON_H,
)

_SETTINGS_BUTTON_W = 200
_SETTINGS_BUTTON_H = 56
_SETTINGS_BUTTON_GAP = 20
# Derived from the Tournament card (now the tallest/lowest of the four)
# rather than a hardcoded Y, so nothing ever overlaps.
_SETTINGS_START_BUTTONS_Y = SETTINGS_TOURNAMENT_CARD_RECT.bottom + 12
_SETTINGS_BUTTONS_START_X = (
    DESIGN_WIDTH - (2 * _SETTINGS_BUTTON_W + _SETTINGS_BUTTON_GAP)
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
# the real window entirely now. When it's taller than DESIGN_HEIGHT, the
# settings screen scrolls within the canvas (see SETTINGS_MAX_SCROLL and
# Renderer._settings_surface) rather than growing the canvas to fit, so
# adding another settings row never risks pushing the design canvas past a
# sensible size.
SETTINGS_CONTENT_HEIGHT = SETTINGS_RESUME_BUTTON_RECT.bottom + 20

# How far the settings screen can scroll past the fixed DESIGN_HEIGHT canvas
# - 0 at today's content height (the whole card stack already fits within
# DESIGN_HEIGHT), but stays real infrastructure for whenever a future
# settings row grows SETTINGS_CONTENT_HEIGHT past it.
SETTINGS_MAX_SCROLL = max(0, SETTINGS_CONTENT_HEIGHT - DESIGN_HEIGHT)

PANEL_PADDING = 24
PANEL_X = BOARD_PX + PANEL_PADDING
PANEL_CONTENT_WIDTH = PANEL_WIDTH - 2 * PANEL_PADDING

PANEL_RECT = pygame.Rect(BOARD_PX, 0, PANEL_WIDTH, DESIGN_HEIGHT)

# The panel is laid out as fixed vertical sections (header / scoreboard /
# status / action button / footer), each given a generous, hand-measured
# height budget so no state's text can ever grow into the next section's
# button - avoids needing a dynamic/reflowing layout for the top section.
PANEL_HEADER_Y = 28
PANEL_DIVIDER_1_Y = 82

PANEL_SCORE_Y = 104
# Row height (was 34, single line) grew to fit a second, smaller "suffix"
# line (enclosure penalty / potential area & flag / skip streak) below the
# name+score+flags line - see DESIGN_HEIGHT above.
PANEL_SCORE_ROW_HEIGHT = 58
PANEL_SCORE_LINE2_DY = 22
PANEL_DIVIDER_2_Y = 216

PANEL_STATUS_Y = 240
PANEL_ACTION_BUTTON_Y = 324

ROLL_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, PANEL_CONTENT_WIDTH, 56)
CONTINUE_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, PANEL_CONTENT_WIDTH, 56)
ROTATE_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, 160, 40)

# Reroll, CHOOSING_PLACEMENT: fills the rest of the row to the right of
# ROTATE_BUTTON_RECT. Only drawn/clickable when reroll_enabled and the
# current player still has charges - Rotate alone (unchanged) otherwise.
_REROLL_PLACEMENT_GAP = 12
REROLL_PLACEMENT_BUTTON_RECT = pygame.Rect(
    ROTATE_BUTTON_RECT.right + _REROLL_PLACEMENT_GAP,
    PANEL_ACTION_BUTTON_Y,
    PANEL_CONTENT_WIDTH - ROTATE_BUTTON_RECT.width - _REROLL_PLACEMENT_GAP,
    40,
)

# Reroll, SKIPPED: splits CONTINUE_BUTTON_RECT's full-width row 50/50, same
# gap pattern as CONFIRM_YES_BUTTON_RECT/CONFIRM_NO_BUTTON_RECT below. Only
# drawn when reroll_enabled and charges remain - CONTINUE_BUTTON_RECT alone
# (unchanged) otherwise.
_SKIP_BUTTON_GAP = 12
_skip_half_w = (PANEL_CONTENT_WIDTH - _SKIP_BUTTON_GAP) // 2
REROLL_SKIPPED_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, _skip_half_w, 56)
SKIP_BUTTON_RECT = pygame.Rect(
    PANEL_X + _skip_half_w + _SKIP_BUTTON_GAP, PANEL_ACTION_BUTTON_Y, _skip_half_w, 56
)

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

# Reroll, CHOOSING_WILDCARD: the only state with real space pressure. The
# 2x3 value grid is centered with slack on both sides (row width 136px of
# the 292px content width) - this drops into the leftover slack on row 2,
# flush to the panel's right edge, rather than shrinking the value buttons.
REROLL_WILDCARD_BUTTON_RECT = pygame.Rect(
    _WILDCARD_ROW_X + 3 * (_WILDCARD_BUTTON_W + _WILDCARD_BUTTON_GAP),
    PANEL_ACTION_BUTTON_Y + (_WILDCARD_BUTTON_H + _WILDCARD_ROW_GAP),
    PANEL_X + PANEL_CONTENT_WIDTH - (_WILDCARD_ROW_X + 3 * (_WILDCARD_BUTTON_W + _WILDCARD_BUTTON_GAP)),
    _WILDCARD_BUTTON_H,
)

# Turn-history log fills the gap between the action button and the footer.
PANEL_HISTORY_DIVIDER_Y = 396
PANEL_HISTORY_LABEL_Y = 410
PANEL_HISTORY_START_Y = 436
PANEL_HISTORY_ROW_HEIGHT = 22
PANEL_HISTORY_MAX_ROWS = 6

# The footer (divider + Surrender/New Game/Exit) anchors to the bottom of
# the fixed DESIGN_HEIGHT canvas - a plain constant now, same as everything
# else here, since the canvas itself never resizes (see compute_scale()).
PANEL_FOOTER_DIVIDER_Y = DESIGN_HEIGHT - 144

SURRENDER_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_FOOTER_DIVIDER_Y + 16, PANEL_CONTENT_WIDTH, 40)

_FOOTER_BUTTON_GAP = 12
_FOOTER_BUTTON_W = (PANEL_CONTENT_WIDTH - _FOOTER_BUTTON_GAP) // 2

NEW_GAME_BUTTON_RECT = pygame.Rect(PANEL_X, DESIGN_HEIGHT - 76, _FOOTER_BUTTON_W, 44)
EXIT_BUTTON_RECT = pygame.Rect(
    PANEL_X + _FOOTER_BUTTON_W + _FOOTER_BUTTON_GAP, DESIGN_HEIGHT - 76, _FOOTER_BUTTON_W, 44
)

# The history log's content never exceeds PANEL_HISTORY_MAX_ROWS, leaving a fixed idle
# gap before the footer divider - the series stats block (when a series is active) lives
# in that gap instead of needing its own dynamic layout. PANEL_SERIES_MAX_ROWS caps that
# block the same way (header + up to this many more lines, truncating older rounds behind
# a "N earlier" note - see Renderer._draw_series_stats) so its height stays bounded
# regardless of series length.
PANEL_SERIES_DIVIDER_Y = 582
PANEL_SERIES_LABEL_Y = 596
PANEL_SERIES_START_Y = 620
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

CONFIRM_DIALOG_RECT = pygame.Rect(
    (DESIGN_WIDTH - _CONFIRM_DIALOG_WIDTH) // 2,
    (DESIGN_HEIGHT - _CONFIRM_DIALOG_HEIGHT) // 2,
    _CONFIRM_DIALOG_WIDTH,
    _CONFIRM_DIALOG_HEIGHT,
)

_CONFIRM_BUTTON_W = 140
_CONFIRM_BUTTON_H = 48
_CONFIRM_BUTTON_GAP = 20
_confirm_buttons_y = CONFIRM_DIALOG_RECT.bottom - 64
_confirm_buttons_x = (DESIGN_WIDTH - (2 * _CONFIRM_BUTTON_W + _CONFIRM_BUTTON_GAP)) // 2

CONFIRM_YES_BUTTON_RECT = pygame.Rect(_confirm_buttons_x, _confirm_buttons_y, _CONFIRM_BUTTON_W, _CONFIRM_BUTTON_H)
CONFIRM_NO_BUTTON_RECT = pygame.Rect(
    _confirm_buttons_x + _CONFIRM_BUTTON_W + _CONFIRM_BUTTON_GAP,
    _confirm_buttons_y,
    _CONFIRM_BUTTON_W,
    _CONFIRM_BUTTON_H,
)

_GAME_OVER_BUTTON_W = 150
_GAME_OVER_BUTTON_H = 48
_GAME_OVER_BUTTON_GAP = 20
_game_over_buttons_y = DESIGN_HEIGHT // 2 + 80
_game_over_buttons_x = (DESIGN_WIDTH - (3 * _GAME_OVER_BUTTON_W + 2 * _GAME_OVER_BUTTON_GAP)) // 2

GAME_OVER_NEW_GAME_BUTTON_RECT = pygame.Rect(
    _game_over_buttons_x, _game_over_buttons_y, _GAME_OVER_BUTTON_W, _GAME_OVER_BUTTON_H
)
GAME_OVER_REPLAY_BUTTON_RECT = pygame.Rect(
    _game_over_buttons_x + _GAME_OVER_BUTTON_W + _GAME_OVER_BUTTON_GAP,
    _game_over_buttons_y,
    _GAME_OVER_BUTTON_W,
    _GAME_OVER_BUTTON_H,
)
GAME_OVER_EXIT_BUTTON_RECT = pygame.Rect(
    _game_over_buttons_x + 2 * (_GAME_OVER_BUTTON_W + _GAME_OVER_BUTTON_GAP),
    _game_over_buttons_y,
    _GAME_OVER_BUTTON_W,
    _GAME_OVER_BUTTON_H,
)

# Only drawn/clickable when a tournament is active - a 4th row below the
# existing 3-button row rather than widening that row's spacing formula, so
# non-tournament games see zero layout change.
GAME_OVER_BRACKET_BUTTON_RECT = pygame.Rect(
    _game_over_buttons_x,
    _game_over_buttons_y + _GAME_OVER_BUTTON_H + _GAME_OVER_BUTTON_GAP,
    3 * _GAME_OVER_BUTTON_W + 2 * _GAME_OVER_BUTTON_GAP,
    _GAME_OVER_BUTTON_H,
)

_REPLAY_BUTTON_W = 110
_REPLAY_BUTTON_H = 44
_REPLAY_BUTTON_GAP = 12
_REPLAY_BUTTON_Y_OFFSET = 76

# Speed-preset keys ride in the same row as Play/Back rather than a row of
# their own - a real render check at the default 19x19 board size showed
# REPLAY_BUTTON_RECTS already overlaps the board's bottom edge slightly, and
# a second row above it would have deepened that overlap; folding the 3
# speed buttons in here keeps the footprint to one row. Widest label ("Back
# (Esc)", measured at 97px against the real font) still fits comfortably in
# the existing 110px button width even at 9 buttons across.
REPLAY_BUTTON_RECTS = _centered_button_row(
    ("first", "prev", "next", "last", "play") + REPLAY_SPEED_PRESETS + ("back",),
    DESIGN_HEIGHT - _REPLAY_BUTTON_Y_OFFSET,
    button_w=_REPLAY_BUTTON_W,
    button_h=_REPLAY_BUTTON_H,
    gap=_REPLAY_BUTTON_GAP,
)

# Turn analysis notes: up to 4 short "missed X" lines below the
# (possibly 2-line-wrapped) caption, in the same idle gap the score chart
# below already lives in - shifting the chart down by _REPLAY_ANALYSIS_DELTA
# rather than growing DESIGN_HEIGHT, same idiom the caption-wrap fix used.
REPLAY_ANALYSIS_Y = 292  # 6px below the caption's worst case: PANEL_STATUS_Y(240) + 2*23

# Room for up to 4 notes (missed flag/denial/self-enclosure always fit on one
# line; the suboptimal-wildcard-pick note can wrap to 2), worst case
# (1+1+1+2)*18=90px, plus margin.
_REPLAY_ANALYSIS_DELTA = 96

# Score-history chart: sits in the large idle gap the replay panel leaves
# between the caption (ends ~264) and the nav button row above (top 808) -
# no DESIGN_HEIGHT growth needed, unlike most panel additions.
REPLAY_SCORE_CHART_LABEL_Y = 300 + _REPLAY_ANALYSIS_DELTA
REPLAY_SCORE_CHART_RECT = pygame.Rect(
    PANEL_X, 326 + _REPLAY_ANALYSIS_DELTA, PANEL_CONTENT_WIDTH, 440 - _REPLAY_ANALYSIS_DELTA
)

# Toggle for revealing each flagged turn's better-scoring candidate - sits in
# the remaining idle gap between the chart's bottom and the nav row above it.
REPLAY_REVEAL_BUTTON_RECT = pygame.Rect(PANEL_X, REPLAY_SCORE_CHART_RECT.bottom + 4, PANEL_CONTENT_WIDTH, 32)

# Screen.TOURNAMENT: one bracket-tree screen, reused for the freshly-seeded
# view, an on-demand mid-tournament check-in, and the completed/champion
# view - simple text columns (one per round) rather than a drawn tree with
# connecting lines, since the round-by-round text already fully conveys the
# state. Column x/width is computed at draw time from the actual round count
# (2 or 3, depending on the 4/8-slot preset), same "small function of a
# runtime value" precedent as cell_px(board_size).
TOURNAMENT_TITLE_Y = 56
TOURNAMENT_COLUMNS_TOP_Y = 140
TOURNAMENT_COLUMNS_MARGIN = 60
TOURNAMENT_ROW_HEIGHT = 40
TOURNAMENT_ACTION_BUTTON_RECT = pygame.Rect((DESIGN_WIDTH - 240) // 2, DESIGN_HEIGHT - 90, 240, 50)


def tournament_column_rect(round_index: int, total_rounds: int) -> pygame.Rect:
    width = (DESIGN_WIDTH - 2 * TOURNAMENT_COLUMNS_MARGIN) // total_rounds
    x = TOURNAMENT_COLUMNS_MARGIN + round_index * width
    return pygame.Rect(x, TOURNAMENT_COLUMNS_TOP_Y, width, DESIGN_HEIGHT - TOURNAMENT_COLUMNS_TOP_Y - 110)
