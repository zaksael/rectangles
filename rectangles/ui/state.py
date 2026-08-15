from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from ..constants import (
    BOARD_SIZE,
    BOT_DIFFICULTY_PRESETS,
    FLAG_CONQUEST_ENABLED,
    OBSTACLES_ENABLED,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT,
    WALLS_ENABLED,
    WILDCARD_ENABLED,
)


class Screen(Enum):
    SETTINGS = auto()
    PLAYING = auto()
    REPLAY = auto()


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
    selected_flag_conquest_enabled: bool = FLAG_CONQUEST_ENABLED
    selected_walls_enabled: bool = WALLS_ENABLED
    selected_obstacles_enabled: bool = OBSTACLES_ENABLED
    selected_wildcard_enabled: bool = WILDCARD_ENABLED
    selected_bot_enabled: bool = False
    selected_bot_difficulty: str = BOT_DIFFICULTY_PRESETS[0]
    selected_series_length: int = SERIES_LENGTH_PRESETS[0]
    game_requested: bool = False
    resume_requested: bool = False
    series_requested: bool = False
    next_game_requested: bool = False

    pending_confirmation: ConfirmAction | None = None
    history_scroll: int = 0
    settings_scroll: int = 0
    replay_step: int = 0

    def reset(self) -> None:
        self.current_dims = None
        self.hover_top_left = None
        self.hover_legal = False
        self.pending_confirmation = None
        self.history_scroll = 0
        self.settings_scroll = 0
        self.replay_step = 0
