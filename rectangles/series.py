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
    scores: dict[int, int] = field(default_factory=lambda: {PLAYER_1: 0, PLAYER_2: 0})
    games_played: int = 0

    def record_game(self, p1_score: int, p2_score: int) -> None:
        self.games_played += 1
        self.scores[PLAYER_1] += p1_score
        self.scores[PLAYER_2] += p2_score

    def is_complete(self) -> bool:
        return self.games_played >= self.length

    def winner(self) -> int | None:
        if self.scores[PLAYER_1] > self.scores[PLAYER_2]:
            return PLAYER_1
        if self.scores[PLAYER_2] > self.scores[PLAYER_1]:
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
