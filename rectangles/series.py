from __future__ import annotations

from dataclasses import dataclass, field

from .constants import FLAG_BONUS_POINTS, PLAYER_1, PLAYER_2
from .game import Game


@dataclass
class Series:
    length: int
    board_size: int
    skip_limit: int
    doubles_enabled: bool = False
    flag_conquest_enabled: bool = False
    flag_bonus_points: int = FLAG_BONUS_POINTS
    wins: dict[int, int] = field(default_factory=lambda: {PLAYER_1: 0, PLAYER_2: 0})
    games_played: int = 0

    @property
    def wins_needed(self) -> int:
        return self.length // 2 + 1

    def record_game(self, winner_id: int | None) -> None:
        self.games_played += 1
        if winner_id is not None:
            self.wins[winner_id] += 1

    def is_complete(self) -> bool:
        return (
            self.wins[PLAYER_1] >= self.wins_needed
            or self.wins[PLAYER_2] >= self.wins_needed
            or self.games_played >= self.length
        )

    def winner(self) -> int | None:
        if self.wins[PLAYER_1] > self.wins[PLAYER_2]:
            return PLAYER_1
        if self.wins[PLAYER_2] > self.wins[PLAYER_1]:
            return PLAYER_2
        return None

    def new_game(self) -> Game:
        return Game(
            board_size=self.board_size,
            skip_limit=self.skip_limit,
            doubles_enabled=self.doubles_enabled,
            flag_conquest_enabled=self.flag_conquest_enabled,
            flag_bonus_points=self.flag_bonus_points,
        )
