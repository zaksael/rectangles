from __future__ import annotations

from dataclasses import dataclass, field

from .constants import FLAG_BONUS_POINTS, PLAYER_1, PLAYER_2
from .game import Game


@dataclass(frozen=True)
class RoundResult:
    area: dict[int, int]
    flags_captured: dict[int, int]
    total: dict[int, int]


@dataclass
class Series:
    length: int
    board_size: int
    skip_limit: int
    flag_conquest_enabled: bool = False
    flag_bonus_points: int = FLAG_BONUS_POINTS
    walls_enabled: bool = False
    wildcard_enabled: bool = False
    scores: dict[int, int] = field(default_factory=lambda: {PLAYER_1: 0, PLAYER_2: 0})
    games_played: int = 0
    rounds: list[RoundResult] = field(default_factory=list)

    def record_game(self, game: Game) -> None:
        self.games_played += 1
        p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
        result = RoundResult(
            area={PLAYER_1: p1.total_area, PLAYER_2: p2.total_area},
            flags_captured={PLAYER_1: p1.flags_captured, PLAYER_2: p2.flags_captured},
            total={PLAYER_1: game.total_score(p1), PLAYER_2: game.total_score(p2)},
        )
        self.rounds.append(result)
        self.scores[PLAYER_1] += result.total[PLAYER_1]
        self.scores[PLAYER_2] += result.total[PLAYER_2]

    def total_flags_captured(self, player_id: int) -> int:
        return sum(r.flags_captured[player_id] for r in self.rounds)

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
            flag_conquest_enabled=self.flag_conquest_enabled,
            flag_bonus_points=self.flag_bonus_points,
            walls_enabled=self.walls_enabled,
            wildcard_enabled=self.wildcard_enabled,
        )
