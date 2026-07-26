from __future__ import annotations

import random
from enum import Enum, auto

from .board import Board
from .constants import (
    BOARD_SIZE,
    DICE_MAX,
    DICE_MIN,
    DOUBLES_ENABLED,
    PLAYER_1,
    PLAYER_2,
    PLAYER_NAMES,
    SKIP_LIMIT,
)
from .models import Player, TurnRecord


class TurnState(Enum):
    AWAITING_ROLL = auto()
    CHOOSING_PLACEMENT = auto()
    SKIPPED = auto()
    GAME_OVER = auto()


class GameOverReason(Enum):
    BOARD_FULL = auto()
    SKIP_LIMIT = auto()
    PLAYER_BLOCKED = auto()
    SURRENDER = auto()


class Game:
    def __init__(
        self,
        board_size: int = BOARD_SIZE,
        skip_limit: int = SKIP_LIMIT,
        doubles_enabled: bool = DOUBLES_ENABLED,
        rng: random.Random | None = None,
    ):
        self.board_size = board_size
        self.skip_limit = skip_limit
        self.doubles_enabled = doubles_enabled
        self.rng = rng or random.Random()
        self.board: Board
        self.players: dict[int, Player]
        self.current_player_id: int
        self.state: TurnState
        self.last_roll: tuple[int, int] | None
        self.legal_cache: dict[tuple[int, int], set[tuple[int, int]]]
        self.game_over_reason: GameOverReason | None
        self.skipped_out_player_id: int | None
        self.blocked_player_id: int | None
        self.surrendered_player_id: int | None
        self.history: list[TurnRecord]
        self.reset()

    def reset(self) -> None:
        self.board = Board(self.board_size)
        self.players = {
            PLAYER_1: Player(PLAYER_1, PLAYER_NAMES[PLAYER_1], (0, 0)),
            PLAYER_2: Player(
                PLAYER_2,
                PLAYER_NAMES[PLAYER_2],
                (self.board_size - 1, self.board_size - 1),
            ),
        }
        self.current_player_id = PLAYER_1
        self.state = TurnState.AWAITING_ROLL
        self.last_roll = None
        self.legal_cache = {}
        self.game_over_reason = None
        self.skipped_out_player_id = None
        self.blocked_player_id = None
        self.surrendered_player_id = None
        self.history = []

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_id]

    def roll_dice(self) -> tuple[int, int]:
        if self.state != TurnState.AWAITING_ROLL:
            raise ValueError(f"Cannot roll dice in state {self.state}")

        a = self.rng.randint(DICE_MIN, DICE_MAX)
        b = self.rng.randint(DICE_MIN, DICE_MAX)
        self.last_roll = (a, b)
        self.legal_cache = self.legal_placements_for_roll()

        if any(self.legal_cache.values()):
            self.state = TurnState.CHOOSING_PLACEMENT
        else:
            self.state = TurnState.SKIPPED
            self.current_player.consecutive_skips += 1
            self.history.append(TurnRecord(self.current_player_id, self.last_roll, placed=None))
        return self.last_roll

    def legal_placements_for_roll(self) -> dict[tuple[int, int], set[tuple[int, int]]]:
        if self.last_roll is None:
            return {}
        a, b = self.last_roll
        player = self.current_player
        return {
            (a, b): self.board.legal_top_lefts(player, a, b),
            (b, a): self.board.legal_top_lefts(player, b, a),
        }

    def attempt_place(self, top_left: tuple[int, int], w: int, h: int) -> bool:
        if self.state != TurnState.CHOOSING_PLACEMENT:
            return False
        legal_set = self.legal_cache.get((w, h))
        if legal_set is None or top_left not in legal_set:
            return False
        rect = self.board.place(self.current_player, top_left, w, h)
        self.current_player.consecutive_skips = 0
        self.history.append(TurnRecord(self.current_player_id, self.last_roll, placed=rect))
        return True

    def end_turn(self) -> None:
        if self.state == TurnState.GAME_OVER:
            return
        is_bonus_turn = (
            self.doubles_enabled and self.last_roll is not None and self.last_roll[0] == self.last_roll[1]
        )
        if not is_bonus_turn:
            self.current_player_id = PLAYER_2 if self.current_player_id == PLAYER_1 else PLAYER_1
        self.last_roll = None
        self.legal_cache = {}
        self.state = TurnState.AWAITING_ROLL

    def surrender(self) -> None:
        if self.state == TurnState.GAME_OVER:
            return
        self.surrendered_player_id = self.current_player_id
        self.game_over_reason = GameOverReason.SURRENDER
        self.state = TurnState.GAME_OVER

    def check_game_over(self) -> bool:
        p1, p2 = self.players[PLAYER_1], self.players[PLAYER_2]
        if not self.board.frontier(p1) and not self.board.frontier(p2):
            self.state = TurnState.GAME_OVER
            self.game_over_reason = GameOverReason.BOARD_FULL
            return True
        for player in (p1, p2):
            if player.has_moved and not self.board.frontier(player):
                self.state = TurnState.GAME_OVER
                self.game_over_reason = GameOverReason.PLAYER_BLOCKED
                self.blocked_player_id = player.id
                return True
        for player in (p1, p2):
            if player.consecutive_skips >= self.skip_limit:
                self.state = TurnState.GAME_OVER
                self.game_over_reason = GameOverReason.SKIP_LIMIT
                self.skipped_out_player_id = player.id
                return True
        return False

    def winner(self) -> int | None:
        if self.game_over_reason == GameOverReason.SURRENDER and self.surrendered_player_id is not None:
            return PLAYER_2 if self.surrendered_player_id == PLAYER_1 else PLAYER_1
        p1, p2 = self.players[PLAYER_1], self.players[PLAYER_2]
        if p1.total_area > p2.total_area:
            return PLAYER_1
        if p2.total_area > p1.total_area:
            return PLAYER_2
        return None
