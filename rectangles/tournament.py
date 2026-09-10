from __future__ import annotations

import random
from dataclasses import dataclass, field

from .constants import (
    BOT_DIFFICULTY_PRESETS,
    PLAYER_1,
    PLAYER_2,
)
from .game import Game
from .series import Series


@dataclass
class Participant:
    name: str
    is_bot: bool = False
    bot_difficulty: str = BOT_DIFFICULTY_PRESETS[0]


@dataclass
class Match:
    participant_a: int  # index into Bracket.participants - always seated PLAYER_1
    participant_b: int  # always seated PLAYER_2
    series: Series | None = None
    tiebreak_game: Game | None = None
    winner: int | None = None  # index into Bracket.participants, once decided


@dataclass
class Bracket:
    participants: list[Participant]
    series_length: int
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
    rng: random.Random = field(default_factory=random.Random)
    rounds: list[list[Match]] = field(default_factory=list)
    current_match_index: int = 0

    def __post_init__(self) -> None:
        if not self.rounds:
            self.rounds = [self._seed_first_round()]

    def _seed_first_round(self) -> list[Match]:
        # Fisher-Yates via self.rng.randint (not rng.shuffle - the injectable
        # rng contract is .randint only, same reason Game's _prize_cells()/
        # _wall_edges()/_obstacle_cells() enumerate-then-pick instead of
        # random.sample/shuffle). Participant count is always a power of 2
        # (enforced by the UI's TOURNAMENT_SIZE_PRESETS), so this is the
        # entire seeding story - no byes anywhere.
        order = list(range(len(self.participants)))
        for i in range(len(order) - 1, 0, -1):
            j = self.rng.randint(0, i)
            order[i], order[j] = order[j], order[i]
        return [Match(order[i], order[i + 1]) for i in range(0, len(order), 2)]

    @property
    def current_round(self) -> list[Match]:
        return self.rounds[-1]

    def current_match(self) -> Match | None:
        round_ = self.current_round
        if self.current_match_index < len(round_):
            return round_[self.current_match_index]
        return None

    def new_series_for_current_match(self) -> Series:
        series = Series(
            length=self.series_length,
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
        self.current_match().series = series
        return series

    def new_tiebreak_game(self) -> Game:
        return Game(
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

    def _tiebreak_winner(self, game: Game) -> int:
        p1_score = game.total_score(game.players[PLAYER_1])
        p2_score = game.total_score(game.players[PLAYER_2])
        if p1_score != p2_score:
            return PLAYER_1 if p1_score > p2_score else PLAYER_2
        # Even the sudden-death tiebreak game can end exactly tied (mirrored
        # start corners plus symmetric house-rule geometry make this more
        # likely here than in an arbitrary game) - break with one coin flip
        # rather than chaining another tiebreak game.
        return PLAYER_1 if self.rng.randint(0, 1) == 0 else PLAYER_2

    def record_match_result(self) -> None:
        match = self.current_match()
        winner = match.series.winner()
        if winner is None:
            if match.tiebreak_game is None:
                return  # caller must build+play a tiebreak game first
            winner = self._tiebreak_winner(match.tiebreak_game)
        match.winner = match.participant_a if winner == PLAYER_1 else match.participant_b

    def advance(self) -> None:
        self.current_match_index += 1
        if self.current_match_index >= len(self.current_round):
            winners = [m.winner for m in self.current_round]
            if len(winners) > 1:
                self.rounds.append([Match(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)])
                self.current_match_index = 0

    def is_complete(self) -> bool:
        return len(self.rounds[-1]) == 1 and self.rounds[-1][0].winner is not None

    def champion(self) -> Participant | None:
        return self.participants[self.rounds[-1][0].winner] if self.is_complete() else None
