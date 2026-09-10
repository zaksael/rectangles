from __future__ import annotations

import pygame

from ..constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    DICE_MAX,
    DICE_MIN,
    GAME_MODE_PRESETS,
    REPLAY_SPEED_PRESETS,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
    TOURNAMENT_SIZE_PRESETS,
)

CELL_PX = 44

# A board's on-screen footprint is capped at TARGET_BOARD_PX regardless of
# board_size (cell_px() shrinks larger boards to fit), so BOARD_PX/DESIGN_WIDTH
# stay fixed even if a bigger board-size tier is added later.
TARGET_BOARD_PX = 836
MAX_BOARD_SIZE = max(BOARD_SIZE_PRESETS)
BOARD_PX = TARGET_BOARD_PX
PANEL_WIDTH = 340

# Everything below is drawn onto a fixed-size canvas at this resolution, then
# scaled to fit the real window. DESIGN_HEIGHT fits the panel's worst case (a
# maxed history log plus a capped series-stats table, see PANEL_*_MAX_ROWS)
# with margin, and never less than the board's footprint.
DESIGN_WIDTH = BOARD_PX + PANEL_WIDTH
DESIGN_HEIGHT = max(BOARD_PX, 884)

# Usability floor for the real OS window, not a layout constraint.
MIN_REAL_WINDOW_WIDTH = 480
MIN_REAL_WINDOW_HEIGHT = 360

# Past ~3x, a scaled design pixel looks visibly blurry. No lower clamp needed -
# MIN_REAL_WINDOW_* keeps the scale from getting that small.
_MAX_SCALE = 3.0


def compute_scale(real_width: int, real_height: int) -> tuple[float, int, int]:
    """Uniform scale + centering offset to fit the design canvas into the real
    window, preserving aspect ratio (cells must stay square); leftover space
    becomes letterbox bars."""
    scale = min(real_width / DESIGN_WIDTH, real_height / DESIGN_HEIGHT)
    scale = min(_MAX_SCALE, scale)
    offset_x = (real_width - round(DESIGN_WIDTH * scale)) // 2
    offset_y = (real_height - round(DESIGN_HEIGHT * scale)) // 2
    return scale, offset_x, offset_y


def to_design_coords(real_x: int, real_y: int, real_width: int, real_height: int) -> tuple[int, int]:
    """Inverse of compute_scale: maps a real-window pixel (e.g. a mouse
    position) back to design-canvas space, where every rect here is defined."""
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


# Game Mode select screen (Screen.MODE_SELECT): 3 stacked mode buttons, then
# Resume (only with a save) and Exit in fixed slots - Exit does not reflow up
# when Resume is absent.
_MODE_BUTTON_W = 340
_MODE_BUTTON_H = 56
_MODE_BUTTON_GAP = 14
_MODE_SECONDARY_GAP = 32
_MODE_SECONDARY_BUTTON_H = 44
_MODE_SECONDARY_BUTTON_GAP = 10

# The button block is centered in the space below the header (DESIGN_HEIGHT is
# sized for the in-game panel, so this screen has spare headroom).
_MODE_CONTENT_TOP = 150
_mode_buttons_block_h = len(GAME_MODE_PRESETS) * _MODE_BUTTON_H + (len(GAME_MODE_PRESETS) - 1) * _MODE_BUTTON_GAP
_mode_secondary_block_h = _MODE_SECONDARY_BUTTON_H * 2 + _MODE_SECONDARY_BUTTON_GAP
_MODE_BUTTONS_TOP = _MODE_CONTENT_TOP + (
    DESIGN_HEIGHT - _MODE_CONTENT_TOP - _mode_buttons_block_h - _MODE_SECONDARY_GAP - _mode_secondary_block_h
) // 2

MODE_SELECT_BUTTON_RECTS = {
    mode: pygame.Rect(
        DESIGN_WIDTH // 2 - _MODE_BUTTON_W // 2,
        _MODE_BUTTONS_TOP + i * (_MODE_BUTTON_H + _MODE_BUTTON_GAP),
        _MODE_BUTTON_W,
        _MODE_BUTTON_H,
    )
    for i, mode in enumerate(GAME_MODE_PRESETS)
}
_mode_buttons_bottom = _MODE_BUTTONS_TOP + _mode_buttons_block_h

MODE_SELECT_RESUME_BUTTON_RECT = pygame.Rect(
    DESIGN_WIDTH // 2 - 100, _mode_buttons_bottom + _MODE_SECONDARY_GAP, 200, _MODE_SECONDARY_BUTTON_H
)
MODE_SELECT_EXIT_BUTTON_RECT = pygame.Rect(
    DESIGN_WIDTH // 2 - 100,
    MODE_SELECT_RESUME_BUTTON_RECT.bottom + _MODE_SECONDARY_BUTTON_GAP,
    200,
    _MODE_SECONDARY_BUTTON_H,
)

# Settings are a single-column list of stacked label+buttons rows, every row's
# button group starting at the same fixed X. Only House Rules has a text header
# above its (chip) row.
SETTINGS_ROWS_TOP = 140  # first row's top, below title/subtitle
SETTINGS_ROW_H = 56
SETTINGS_ROW_GAP = 12
SETTINGS_HOUSE_RULES_HEADER_H = 34
SETTINGS_HOUSE_RULES_CHIP_ROW_H = 50
SETTINGS_TOURNAMENT_SLOT_ROW_H = 40

SETTINGS_FORM_LABEL_X = DESIGN_WIDTH // 2 - 260
SETTINGS_FORM_BUTTONS_X = DESIGN_WIDTH // 2 - 60

_ROW_BUTTON_H = 44
_ROW_BUTTON_PAD = (SETTINGS_ROW_H - _ROW_BUTTON_H) // 2
_TOURNAMENT_SLOT_BUTTON_H = 32
_TOURNAMENT_SLOT_BUTTON_PAD = (SETTINGS_TOURNAMENT_SLOT_ROW_H - _TOURNAMENT_SLOT_BUTTON_H) // 2


# The row list and ordering: single source of truth for the Y math below and
# renderer.py's draw loop (via settings_row_ids()). Board Size/Skip Limit are
# always first, so their rects stay plain constants below. Series Length also
# applies to Tournament mode (a match is a Series under the hood).
def _settings_rows(mode: str, tournament_size: int) -> list[tuple[str, int]]:
    rows = [("board_size", SETTINGS_ROW_H), ("skip_limit", SETTINGS_ROW_H)]
    if mode != "Tournament":
        rows.append(("opponent", SETTINGS_ROW_H))
    if mode != "Single":
        rows.append(("series_length", SETTINGS_ROW_H))
    if mode == "Tournament":
        rows.append(("tournament_size", SETTINGS_ROW_H))
        rows += [(f"tournament_slot_{i}", SETTINGS_TOURNAMENT_SLOT_ROW_H) for i in range(tournament_size)]
    rows.append(("house_rules", SETTINGS_HOUSE_RULES_HEADER_H + SETTINGS_HOUSE_RULES_CHIP_ROW_H))
    return rows


def settings_row_ids(mode: str, tournament_size: int) -> list[str]:
    return [row_id for row_id, _ in _settings_rows(mode, tournament_size)]


def settings_row_top(mode: str, tournament_size: int, row_id: str) -> int:
    y = SETTINGS_ROWS_TOP
    for rid, h in _settings_rows(mode, tournament_size):
        if rid == row_id:
            return y
        y += h + SETTINGS_ROW_GAP
    raise ValueError(row_id)


def _content_bottom(mode: str, tournament_size: int) -> int:
    y = SETTINGS_ROWS_TOP
    for _, h in _settings_rows(mode, tournament_size):
        y += h + SETTINGS_ROW_GAP
    return y - SETTINGS_ROW_GAP


def _row_buttons(
    values: tuple, y: int, button_w: int, start_x: int = SETTINGS_FORM_BUTTONS_X, button_h: int = _ROW_BUTTON_H, gap: int = 12
) -> dict:
    return {v: pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h) for i, v in enumerate(values)}


SETTINGS_BOARD_SIZE_BUTTON_RECTS = _row_buttons(BOARD_SIZE_PRESETS, y=SETTINGS_ROWS_TOP + _ROW_BUTTON_PAD, button_w=90)
SETTINGS_SKIP_LIMIT_BUTTON_RECTS = _row_buttons(
    SKIP_LIMIT_PRESETS, y=SETTINGS_ROWS_TOP + SETTINGS_ROW_H + SETTINGS_ROW_GAP + _ROW_BUTTON_PAD, button_w=90
)


# The Opponent row only exists outside Tournament mode (which has per-slot bot config).
def settings_opponent_button_rects(mode: str, tournament_size: int) -> dict[str, pygame.Rect]:
    y = settings_row_top(mode, tournament_size, "opponent") + _ROW_BUTTON_PAD
    return _row_buttons(("Human",) + BOT_DIFFICULTY_PRESETS, y=y, button_w=100)


def settings_series_length_button_rects(mode: str, tournament_size: int) -> dict[int, pygame.Rect]:
    y = settings_row_top(mode, tournament_size, "series_length") + _ROW_BUTTON_PAD
    return _row_buttons(SERIES_LENGTH_PRESETS, y=y, button_w=120)


def settings_tournament_size_button_rects(tournament_size: int) -> dict[int, pygame.Rect]:
    y = settings_row_top("Tournament", tournament_size, "tournament_size") + _ROW_BUTTON_PAD
    return _row_buttons(TOURNAMENT_SIZE_PRESETS, y=y, button_w=90, gap=16)


# Per-slot rows are sized to the selected tournament_size, not the max preset,
# so switching 4<->8 slots actually grows/shrinks the row list.
_TOURNAMENT_SLOT_TOGGLE_W = 100
_TOURNAMENT_SLOT_DIFFICULTY_X = SETTINGS_FORM_BUTTONS_X + _TOURNAMENT_SLOT_TOGGLE_W + 20
_TOURNAMENT_SLOT_DIFFICULTY_BUTTON_W = 78
_TOURNAMENT_SLOT_DIFFICULTY_GAP = 8


def settings_tournament_slot_toggle_rect(tournament_size: int, i: int) -> pygame.Rect:
    y = settings_row_top("Tournament", tournament_size, f"tournament_slot_{i}") + _TOURNAMENT_SLOT_BUTTON_PAD
    return pygame.Rect(SETTINGS_FORM_BUTTONS_X, y, _TOURNAMENT_SLOT_TOGGLE_W, _TOURNAMENT_SLOT_BUTTON_H)


def settings_tournament_slot_difficulty_rects(tournament_size: int, i: int) -> dict[str, pygame.Rect]:
    y = settings_row_top("Tournament", tournament_size, f"tournament_slot_{i}") + _TOURNAMENT_SLOT_BUTTON_PAD
    return {
        value: pygame.Rect(
            _TOURNAMENT_SLOT_DIFFICULTY_X + j * (_TOURNAMENT_SLOT_DIFFICULTY_BUTTON_W + _TOURNAMENT_SLOT_DIFFICULTY_GAP),
            y,
            _TOURNAMENT_SLOT_DIFFICULTY_BUTTON_W,
            _TOURNAMENT_SLOT_BUTTON_H,
        )
        for j, value in enumerate(BOT_DIFFICULTY_PRESETS)
    }


# House Rules: one centered row of short chips, with "Turn All ON/OFF" beside
# the header. /render-check before adding a 10th - the row is nearly full.
_HOUSE_RULE_LABELS = ("Prize", "Walls", "Obstacles", "Pitfall", "Steal", "Wildcard", "Enclosure", "Reroll", "Comeback")
_RULE_BUTTON_W = 110
_RULE_BUTTON_H = 40


def settings_house_rule_button_rects(mode: str, tournament_size: int) -> dict[str, pygame.Rect]:
    top = settings_row_top(mode, tournament_size, "house_rules")
    y = top + SETTINGS_HOUSE_RULES_HEADER_H + (SETTINGS_HOUSE_RULES_CHIP_ROW_H - _RULE_BUTTON_H) // 2
    return _centered_button_row(_HOUSE_RULE_LABELS, y=y, button_w=_RULE_BUTTON_W, button_h=_RULE_BUTTON_H, gap=12)


def settings_all_rules_button_rect(mode: str, tournament_size: int) -> pygame.Rect:
    top = settings_row_top(mode, tournament_size, "house_rules")
    right_edge = max(rect.right for rect in settings_house_rule_button_rects(mode, tournament_size).values())
    return pygame.Rect(right_edge - 150, top + 4, 150, 26)


_SETTINGS_BUTTON_W = 200
_SETTINGS_BUTTON_H = 56
_SETTINGS_BUTTON_GAP = 20
# 2-button-wide centered span for the secondary (Exit/Back) row.
_SETTINGS_BUTTONS_START_X = (
    DESIGN_WIDTH - (2 * _SETTINGS_BUTTON_W + _SETTINGS_BUTTON_GAP)
) // 2

_SETTINGS_SECONDARY_BUTTON_H = 48


def settings_action_row_y(mode: str, tournament_size: int) -> int:
    return _content_bottom(mode, tournament_size) + 20


# Fits the longest label, "Start Tournament (Space)" (~230px at the panel font).
_SETTINGS_START_BUTTON_W = 260


def settings_start_button_rect(mode: str, tournament_size: int) -> pygame.Rect:
    return pygame.Rect(
        DESIGN_WIDTH // 2 - _SETTINGS_START_BUTTON_W // 2,
        settings_action_row_y(mode, tournament_size),
        _SETTINGS_START_BUTTON_W,
        _SETTINGS_BUTTON_H,
    )


def _settings_secondary_row_y(mode: str, tournament_size: int) -> int:
    return settings_action_row_y(mode, tournament_size) + _SETTINGS_BUTTON_H + 12


# Exit / Back share one centered row below the Start button. Back returns to
# the Game Mode select screen.
def settings_exit_button_rect(mode: str, tournament_size: int) -> pygame.Rect:
    return pygame.Rect(
        _SETTINGS_BUTTONS_START_X,
        _settings_secondary_row_y(mode, tournament_size),
        _SETTINGS_BUTTON_W,
        _SETTINGS_SECONDARY_BUTTON_H,
    )


def settings_back_button_rect(mode: str, tournament_size: int) -> pygame.Rect:
    return pygame.Rect(
        _SETTINGS_BUTTONS_START_X + _SETTINGS_BUTTON_W + _SETTINGS_BUTTON_GAP,
        _settings_secondary_row_y(mode, tournament_size),
        _SETTINGS_BUTTON_W,
        _SETTINGS_SECONDARY_BUTTON_H,
    )


# Full settings button stack height for a mode/size. When taller than
# DESIGN_HEIGHT the screen scrolls (settings_max_scroll) rather than growing
# the canvas.
def settings_content_height(mode: str, tournament_size: int) -> int:
    return settings_back_button_rect(mode, tournament_size).bottom + 20


def settings_max_scroll(mode: str, tournament_size: int) -> int:
    return max(0, settings_content_height(mode, tournament_size) - DESIGN_HEIGHT)


# Tournament at the largest slot preset is the tallest case;
# Renderer._settings_surface is allocated once for it before any mode is chosen.
SETTINGS_CONTENT_HEIGHT_MAX = settings_content_height("Tournament", max(TOURNAMENT_SIZE_PRESETS))

PANEL_PADDING = 24
PANEL_X = BOARD_PX + PANEL_PADDING
PANEL_CONTENT_WIDTH = PANEL_WIDTH - 2 * PANEL_PADDING

PANEL_RECT = pygame.Rect(BOARD_PX, 0, PANEL_WIDTH, DESIGN_HEIGHT)

# The panel has fixed vertical sections (header / scoreboard / status / action
# button / footer), each with a hand-measured height budget so no state's text
# grows into the next section.
PANEL_HEADER_Y = 28
PANEL_DIVIDER_1_Y = 82

PANEL_SCORE_Y = 104
# Tall enough for the suffix line to wrap to two lines (up to ~6 items with
# every house rule on), plus 8px margin above PANEL_DIVIDER_2_Y.
PANEL_SCORE_ROW_HEIGHT = 66
PANEL_SCORE_LINE2_DY = 22
PANEL_DIVIDER_2_Y = 232

PANEL_STATUS_Y = 256
PANEL_ACTION_BUTTON_Y = 324

ROLL_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, PANEL_CONTENT_WIDTH, 56)
CONTINUE_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, PANEL_CONTENT_WIDTH, 56)
ROTATE_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, 160, 40)

# Reroll, CHOOSING_PLACEMENT: fills the row right of ROTATE_BUTTON_RECT. Only
# drawn when can_reroll(), else Rotate alone.
_REROLL_PLACEMENT_GAP = 12
REROLL_PLACEMENT_BUTTON_RECT = pygame.Rect(
    ROTATE_BUTTON_RECT.right + _REROLL_PLACEMENT_GAP,
    PANEL_ACTION_BUTTON_Y,
    PANEL_CONTENT_WIDTH - ROTATE_BUTTON_RECT.width - _REROLL_PLACEMENT_GAP,
    40,
)

# Reroll, SKIPPED: splits CONTINUE_BUTTON_RECT's row 50/50. Only drawn when
# can_reroll(), else Continue alone.
_SKIP_BUTTON_GAP = 12
_skip_half_w = (PANEL_CONTENT_WIDTH - _SKIP_BUTTON_GAP) // 2
REROLL_SKIPPED_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_ACTION_BUTTON_Y, _skip_half_w, 56)
SKIP_BUTTON_RECT = pygame.Rect(
    PANEL_X + _skip_half_w + _SKIP_BUTTON_GAP, PANEL_ACTION_BUTTON_Y, _skip_half_w, 56
)

# 2x3 grid: the gap before PANEL_HISTORY_DIVIDER_Y only fits two 32px rows.
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

# Reroll, CHOOSING_WILDCARD: drops into the slack right of the centered 2x3
# value grid on row 2, flush to the panel's right edge.
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

# The footer (Surrender/New Game/Exit) anchors to the canvas bottom.
PANEL_FOOTER_DIVIDER_Y = DESIGN_HEIGHT - 144

SURRENDER_BUTTON_RECT = pygame.Rect(PANEL_X, PANEL_FOOTER_DIVIDER_Y + 16, PANEL_CONTENT_WIDTH, 40)

_FOOTER_BUTTON_GAP = 12
_FOOTER_BUTTON_W = (PANEL_CONTENT_WIDTH - _FOOTER_BUTTON_GAP) // 2

NEW_GAME_BUTTON_RECT = pygame.Rect(PANEL_X, DESIGN_HEIGHT - 76, _FOOTER_BUTTON_W, 44)
EXIT_BUTTON_RECT = pygame.Rect(
    PANEL_X + _FOOTER_BUTTON_W + _FOOTER_BUTTON_GAP, DESIGN_HEIGHT - 76, _FOOTER_BUTTON_W, 44
)

# The series stats block (when a series is active) lives in the fixed gap
# between the capped history log and the footer. PANEL_SERIES_MAX_ROWS caps it
# so its height stays bounded regardless of series length.
PANEL_SERIES_DIVIDER_Y = 582
PANEL_SERIES_LABEL_Y = 596
PANEL_SERIES_START_Y = 620
PANEL_SERIES_ROW_HEIGHT = 20
PANEL_SERIES_MAX_ROWS = 5

# Mouse-wheel hit region for the history log; stops at the series stats section.
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

# Only drawn when a tournament is active - a 4th row below the 3-button row,
# so non-tournament games see no layout change.
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

# All nav + speed + Back buttons share one row (a second row would overlap the
# board's bottom edge). Widest label "Back (Esc)" (~97px) fits the 110px width.
REPLAY_BUTTON_RECTS = _centered_button_row(
    ("first", "prev", "next", "last", "play") + REPLAY_SPEED_PRESETS + ("back",),
    DESIGN_HEIGHT - _REPLAY_BUTTON_Y_OFFSET,
    button_w=_REPLAY_BUTTON_W,
    button_h=_REPLAY_BUTTON_H,
    gap=_REPLAY_BUTTON_GAP,
)

# Turn analysis: one "missed X" note below the (possibly wrapped) caption; the
# chart below shifts down by _REPLAY_ANALYSIS_DELTA to make room.
REPLAY_ANALYSIS_Y = 292  # 6px below the caption's worst case: PANEL_STATUS_Y(240) + 2*23

# Room for the note's worst case, 2 wrapped lines plus margin.
_REPLAY_ANALYSIS_DELTA = 48

# Score-history chart: fits in the replay panel's idle gap, no DESIGN_HEIGHT growth.
REPLAY_SCORE_CHART_LABEL_Y = 300 + _REPLAY_ANALYSIS_DELTA
REPLAY_SCORE_CHART_RECT = pygame.Rect(
    PANEL_X, 326 + _REPLAY_ANALYSIS_DELTA, PANEL_CONTENT_WIDTH, 440 - _REPLAY_ANALYSIS_DELTA
)

# Toggle for revealing each flagged turn's better-scoring candidate.
REPLAY_REVEAL_BUTTON_RECT = pygame.Rect(PANEL_X, REPLAY_SCORE_CHART_RECT.bottom + 4, PANEL_CONTENT_WIDTH, 32)

# Screen.TOURNAMENT: rounds drawn as text columns (one per round), not a tree.
# Column x/width is computed at draw time from the round count.
TOURNAMENT_TITLE_Y = 56
TOURNAMENT_COLUMNS_TOP_Y = 140
TOURNAMENT_COLUMNS_MARGIN = 60
TOURNAMENT_ROW_HEIGHT = 40
TOURNAMENT_ACTION_BUTTON_RECT = pygame.Rect((DESIGN_WIDTH - 240) // 2, DESIGN_HEIGHT - 90, 240, 50)


def tournament_column_rect(round_index: int, total_rounds: int) -> pygame.Rect:
    width = (DESIGN_WIDTH - 2 * TOURNAMENT_COLUMNS_MARGIN) // total_rounds
    x = TOURNAMENT_COLUMNS_MARGIN + round_index * width
    return pygame.Rect(x, TOURNAMENT_COLUMNS_TOP_Y, width, DESIGN_HEIGHT - TOURNAMENT_COLUMNS_TOP_Y - 110)
