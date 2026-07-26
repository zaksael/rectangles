from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ..constants import BOARD_SIZE, DOUBLES_ENABLED, SERIES_LENGTH_PRESETS, SKIP_LIMIT


class Screen(Enum):
    SETTINGS = auto()
    PLAYING = auto()


class ConfirmAction(Enum):
    NEW_GAME = auto()
    EXIT = auto()
    SURRENDER = auto()


@dataclass
class UIState:
    current_dims: tuple[int, int] | None = None
    hover_top_left: tuple[int, int] | None = None
    hover_legal: bool = False

    screen: Screen = Screen.SETTINGS
    selected_board_size: int = BOARD_SIZE
    selected_skip_limit: int = SKIP_LIMIT
    selected_doubles_enabled: bool = DOUBLES_ENABLED
    selected_bot_enabled: bool = False
    selected_series_length: int = SERIES_LENGTH_PRESETS[0]
    game_requested: bool = False
    resume_requested: bool = False
    series_requested: bool = False
    next_game_requested: bool = False

    pending_confirmation: ConfirmAction | None = None
    history_scroll: int = 0

    def reset(self) -> None:
        self.current_dims = None
        self.hover_top_left = None
        self.hover_legal = False
        self.pending_confirmation = None
        self.history_scroll = 0
