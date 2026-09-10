from __future__ import annotations

from dataclasses import dataclass, field

from .constants import CellKind, PLAYER_1, PLAYER_2
from .game import Game


@dataclass(frozen=True)
class RoundResult:
    area: dict[int, int]
    prize_captured: dict[int, int]
    total: dict[int, int]


@dataclass
class Series:
    length: int
    board_size: int
    skip_limit: int
    prize_enabled: bool = False
    walls_enabled: bool = False
    obstacles_enabled: bool = False
    pitfall_enabled: bool = False
    steal_enabled: bool = False
    special_cell_points: dict[str, int] = field(default_factory=dict)
    wildcard_enabled: bool = False
    self_enclosed_penalty_enabled: bool = False
    reroll_enabled: bool = False
    comeback_nudge_enabled: bool = False
    scores: dict[int, int] = field(default_factory=lambda: {PLAYER_1: 0, PLAYER_2: 0})
    games_played: int = 0
    rounds: list[RoundResult] = field(default_factory=list)

    def record_game(self, game: Game) -> None:
        self.games_played += 1
        p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
        result = RoundResult(
            area={PLAYER_1: p1.total_area, PLAYER_2: p2.total_area},
            prize_captured={
                PLAYER_1: p1.special_captures.get(CellKind.PRIZE, 0),
                PLAYER_2: p2.special_captures.get(CellKind.PRIZE, 0),
            },
            total={PLAYER_1: game.total_score(p1), PLAYER_2: game.total_score(p2)},
        )
        self.rounds.append(result)
        self.scores[PLAYER_1] += result.total[PLAYER_1]
        self.scores[PLAYER_2] += result.total[PLAYER_2]

    def total_prize_captured(self, player_id: int) -> int:
        return sum(r.prize_captured[player_id] for r in self.rounds)

    def is_complete(self) -> bool:
        return self.games_played >= self.length

    def winner(self) -> int | None:
        if self.scores[PLAYER_1] > self.scores[PLAYER_2]:
            return PLAYER_1
        if self.scores[PLAYER_2] > self.scores[PLAYER_1]:
            return PLAYER_2
        return None

    def new_game(self) -> Game:
        game = Game(
            board_size=self.board_size,
            skip_limit=self.skip_limit,
            prize_enabled=self.prize_enabled,
            walls_enabled=self.walls_enabled,
            obstacles_enabled=self.obstacles_enabled,
            pitfall_enabled=self.pitfall_enabled,
            steal_enabled=self.steal_enabled,
            special_cell_points=self.special_cell_points,
            wildcard_enabled=self.wildcard_enabled,
            self_enclosed_penalty_enabled=self.self_enclosed_penalty_enabled,
            reroll_enabled=self.reroll_enabled,
            comeback_nudge_enabled=self.comeback_nudge_enabled,
        )
        game.current_player_id = PLAYER_1 if self.games_played % 2 == 0 else PLAYER_2
        return game
