from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from ..engine.constants import (
    BOARD_SIZE,
    BOT_DIFFICULTY_PRESETS,
    COMEBACK_NUDGE_ENABLED,
    STEAL_ENABLED,
    PRIZE_ENABLED,
    GAME_MODE_PRESETS,
    PITFALL_ENABLED,
    OBSTACLES_ENABLED,
    REPLAY_SPEED_PRESETS,
    REROLL_ENABLED,
    SELF_ENCLOSED_PENALTY_ENABLED,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT,
    TOURNAMENT_SIZE_PRESETS,
    WALLS_ENABLED,
    WILDCARD_ENABLED,
)


class Screen(Enum):
    MODE_SELECT = auto()
    SETTINGS = auto()
    PLAYING = auto()
    REPLAY = auto()
    TOURNAMENT = auto()


class ConfirmAction(Enum):
    NEW_GAME = auto()
    EXIT = auto()
    SURRENDER = auto()


@dataclass
class UIState:
    current_dims: tuple[int, int] | None = None
    hover_top_left: tuple[int, int] | None = None
    hover_legal: bool = False

    screen: Screen = Screen.MODE_SELECT
    server_mode: bool = False
    selected_game_mode: str = GAME_MODE_PRESETS[0]
    selected_board_size: int = BOARD_SIZE
    selected_skip_limit: int = SKIP_LIMIT
    selected_prize_enabled: bool = PRIZE_ENABLED
    selected_walls_enabled: bool = WALLS_ENABLED
    selected_obstacles_enabled: bool = OBSTACLES_ENABLED
    selected_pitfall_enabled: bool = PITFALL_ENABLED
    selected_steal_enabled: bool = STEAL_ENABLED
    selected_wildcard_enabled: bool = WILDCARD_ENABLED
    selected_self_enclosed_penalty_enabled: bool = SELF_ENCLOSED_PENALTY_ENABLED
    selected_reroll_enabled: bool = REROLL_ENABLED
    selected_comeback_nudge_enabled: bool = COMEBACK_NUDGE_ENABLED
    selected_bot_enabled: bool = False
    selected_bot_difficulty: str = BOT_DIFFICULTY_PRESETS[0]
    selected_series_length: int = SERIES_LENGTH_PRESETS[0]
    active_bot_seats: dict[int, str] = field(default_factory=dict)
    game_requested: bool = False
    resume_requested: bool = False
    series_requested: bool = False
    next_game_requested: bool = False

    tournament_size: int = TOURNAMENT_SIZE_PRESETS[0]
    tournament_slot_is_bot: list[bool] = field(
        default_factory=lambda: [False] * max(TOURNAMENT_SIZE_PRESETS)
    )
    tournament_slot_difficulty: list[str] = field(
        default_factory=lambda: [BOT_DIFFICULTY_PRESETS[0]] * max(TOURNAMENT_SIZE_PRESETS)
    )
    tournament_requested: bool = False
    begin_match_requested: bool = False
    next_match_requested: bool = False

    pending_confirmation: ConfirmAction | None = None
    history_scroll: int = 0
    settings_scroll: int = 0
    replay_step: int = 0
    replay_autoplay: bool = False
    replay_speed: str = REPLAY_SPEED_PRESETS[1]
    replay_show_better_option: bool = False

    def reset(self) -> None:
        self.current_dims = None
        self.hover_top_left = None
        self.hover_legal = False
        self.pending_confirmation = None
        self.history_scroll = 0
        self.settings_scroll = 0
        self.replay_step = 0

    @property
    def wildcard_reroll_locked(self) -> bool:
        # Not proxied through the server adapter - see app.py's
        # _HOUSE_RULE_QUERY_PARAMS - so these two stay off and unclickable
        # for a server-backed Single-mode game.
        return self.server_mode and self.selected_game_mode == "Single"

    @property
    def all_house_rules_enabled(self) -> bool:
        rules = [
            self.selected_prize_enabled,
            self.selected_walls_enabled,
            self.selected_obstacles_enabled,
            self.selected_pitfall_enabled,
            self.selected_steal_enabled,
            self.selected_self_enclosed_penalty_enabled,
            self.selected_comeback_nudge_enabled,
        ]
        if not self.wildcard_reroll_locked:
            rules += [self.selected_wildcard_enabled, self.selected_reroll_enabled]
        return all(rules)

    def toggle_all_house_rules(self) -> None:
        value = not self.all_house_rules_enabled
        self.selected_prize_enabled = value
        self.selected_walls_enabled = value
        self.selected_obstacles_enabled = value
        self.selected_pitfall_enabled = value
        self.selected_steal_enabled = value
        self.selected_self_enclosed_penalty_enabled = value
        self.selected_comeback_nudge_enabled = value
        if not self.wildcard_reroll_locked:
            self.selected_wildcard_enabled = value
            self.selected_reroll_enabled = value
