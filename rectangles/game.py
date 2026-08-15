from __future__ import annotations

import random
from enum import Enum, auto

from .board import Board
from .constants import (
    BOARD_SIZE,
    DICE_MAX,
    DICE_MIN,
    FLAG_BONUS_POINTS,
    FLAG_CONQUEST_ENABLED,
    OBSTACLE_CELL_PAIRS,
    OBSTACLES_ENABLED,
    PLAYER_1,
    PLAYER_2,
    PLAYER_NAMES,
    SKIP_LIMIT,
    START_CORNER_EXCLUSION_RADIUS,
    WALL_LINE_LENGTH,
    WALL_LINE_PAIRS,
    WALLS_ENABLED,
    WILDCARD_ENABLED,
)
from .models import Player, TurnRecord


class TurnState(Enum):
    AWAITING_ROLL = auto()
    CHOOSING_WILDCARD = auto()
    CHOOSING_PLACEMENT = auto()
    SKIPPED = auto()
    GAME_OVER = auto()


class GameOverReason(Enum):
    BOARD_FULL = auto()
    SKIP_LIMIT = auto()
    PLAYER_BLOCKED = auto()
    SURRENDER = auto()


def _mirror_cell(cell: tuple[int, int], size: int) -> tuple[int, int]:
    r, c = cell
    return (size - 1 - r, size - 1 - c)


def _near_start_corner(cell: tuple[int, int], size: int) -> bool:
    r, c = cell
    corners = ((0, 0), (size - 1, size - 1))
    return any(max(abs(r - cr), abs(c - cc)) <= START_CORNER_EXCLUSION_RADIUS for cr, cc in corners)


class Game:
    def __init__(
        self,
        board_size: int = BOARD_SIZE,
        skip_limit: int = SKIP_LIMIT,
        flag_conquest_enabled: bool = FLAG_CONQUEST_ENABLED,
        flag_bonus_points: int = FLAG_BONUS_POINTS,
        walls_enabled: bool = WALLS_ENABLED,
        obstacles_enabled: bool = OBSTACLES_ENABLED,
        wildcard_enabled: bool = WILDCARD_ENABLED,
        rng: random.Random | None = None,
    ):
        self.board_size = board_size
        self.skip_limit = skip_limit
        self.flag_conquest_enabled = flag_conquest_enabled
        self.flag_bonus_points = flag_bonus_points
        self.walls_enabled = walls_enabled
        self.obstacles_enabled = obstacles_enabled
        self.wildcard_enabled = wildcard_enabled
        self.rng = rng or random.Random()
        self.board: Board
        self.players: dict[int, Player]
        self.current_player_id: int
        self.state: TurnState
        self.last_roll: tuple[int, int] | None
        self.wildcard_index: int | None
        self.wildcard_original_roll: tuple[int, int] | None
        self.legal_cache: dict[tuple[int, int], set[tuple[int, int]]]
        self.game_over_reason: GameOverReason | None
        self.skipped_out_player_id: int | None
        self.blocked_player_id: int | None
        self.surrendered_player_id: int | None
        self.history: list[TurnRecord]
        self.reset()

    def reset(self) -> None:
        size = self.board_size
        flag_cells = self._flag_cells() if self.flag_conquest_enabled else frozenset()
        wall_edges = self._wall_edges(flag_cells) if self.walls_enabled else frozenset()
        obstacle_cells = (
            self._obstacle_cells(flag_cells, wall_edges) if self.obstacles_enabled else frozenset()
        )
        self.board = Board(
            self.board_size,
            flag_cells=flag_cells,
            wall_edges=wall_edges,
            obstacle_cells=obstacle_cells,
        )
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
        self.wildcard_index = None
        self.wildcard_original_roll = None
        self.legal_cache = {}
        self.game_over_reason = None
        self.skipped_out_player_id = None
        self.blocked_player_id = None
        self.surrendered_player_id = None
        self.history = []

    def _flag_cells(self) -> frozenset[tuple[int, int]]:
        size = self.board_size
        center = (size // 2, size // 2)

        candidates = [
            (r, c)
            for r in range(size)
            for c in range(size)
            if (r, c) != center and not _near_start_corner((r, c), size)
        ]
        if not candidates:
            return frozenset({center})
        cell = candidates[self.rng.randint(0, len(candidates) - 1)]
        return frozenset({center, cell, _mirror_cell(cell, size)})

    def _wall_edges(
        self, flag_cells: frozenset[tuple[int, int]]
    ) -> frozenset[frozenset[tuple[int, int]]]:
        size = self.board_size

        def segment_edges(
            horizontal: bool, fixed: int, start: int
        ) -> list[frozenset[tuple[int, int]]]:
            if horizontal:
                return [frozenset({(fixed, i), (fixed + 1, i)}) for i in range(start, start + WALL_LINE_LENGTH)]
            return [frozenset({(i, fixed), (i, fixed + 1)}) for i in range(start, start + WALL_LINE_LENGTH)]

        occupied: set[tuple[int, int]] = set(flag_cells)
        result: set[frozenset[tuple[int, int]]] = set()

        for _ in range(WALL_LINE_PAIRS):
            horizontal = self.rng.randint(0, 1) == 0
            candidates: list[list[frozenset[tuple[int, int]]]] = []
            for fixed in range(size - 1):
                for start in range(size - WALL_LINE_LENGTH + 1):
                    edges = segment_edges(horizontal, fixed, start)
                    cells = set().union(*edges)
                    if cells & {_mirror_cell(cell, size) for cell in cells}:
                        continue
                    if any(_near_start_corner(cell, size) for cell in cells) or cells & occupied:
                        continue
                    candidates.append(edges)
            if not candidates:
                continue
            edges = candidates[self.rng.randint(0, len(candidates) - 1)]
            mirrored_edges = [frozenset(_mirror_cell(c, size) for c in edge) for edge in edges]
            occupied |= set().union(*edges, *mirrored_edges)
            result.update(edges)
            result.update(mirrored_edges)

        return frozenset(result)

    def _obstacle_cells(
        self,
        flag_cells: frozenset[tuple[int, int]],
        wall_edges: frozenset[frozenset[tuple[int, int]]],
    ) -> frozenset[tuple[int, int]]:
        size = self.board_size
        occupied: set[tuple[int, int]] = set(flag_cells) | {cell for edge in wall_edges for cell in edge}
        result: set[tuple[int, int]] = set()

        for _ in range(OBSTACLE_CELL_PAIRS):
            candidates = [
                (r, c)
                for r in range(size)
                for c in range(size)
                if (r, c) not in occupied and not _near_start_corner((r, c), size)
            ]
            if not candidates:
                continue
            cell = candidates[self.rng.randint(0, len(candidates) - 1)]
            mirrored = _mirror_cell(cell, size)
            occupied.add(cell)
            occupied.add(mirrored)
            result.add(cell)
            result.add(mirrored)

        return frozenset(result)

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_id]

    def roll_dice(self) -> tuple[int, int]:
        if self.state != TurnState.AWAITING_ROLL:
            raise ValueError(f"Cannot roll dice in state {self.state}")

        a = self.rng.randint(DICE_MIN, DICE_MAX)
        b = self.rng.randint(DICE_MIN, DICE_MAX)
        self.last_roll = (a, b)

        if self.wildcard_enabled and a == b:
            self.wildcard_original_roll = self.last_roll
            self.wildcard_index = self.rng.randint(0, 1)
            self.state = TurnState.CHOOSING_WILDCARD
            return self.last_roll

        self._resolve_roll()
        return self.last_roll

    def choose_wildcard_value(self, value: int) -> None:
        if self.state != TurnState.CHOOSING_WILDCARD:
            raise ValueError(f"Cannot choose a wildcard value in state {self.state}")
        if not (DICE_MIN <= value <= DICE_MAX):
            raise ValueError(f"Wildcard value must be between {DICE_MIN} and {DICE_MAX}, got {value}")

        a, b = self.last_roll
        if self.wildcard_index == 0:
            a = value
        else:
            b = value
        self.last_roll = (a, b)
        self.wildcard_index = None
        self._resolve_roll()

    def _resolve_roll(self) -> None:
        self.legal_cache = self.legal_placements_for_roll()
        if any(self.legal_cache.values()):
            self.state = TurnState.CHOOSING_PLACEMENT
        else:
            self.state = TurnState.SKIPPED
            self.current_player.consecutive_skips += 1
            self.history.append(
                TurnRecord(
                    self.current_player_id,
                    self.last_roll,
                    placed=None,
                    wildcard_original_roll=self.wildcard_original_roll,
                )
            )

    def legal_placements_for_roll(self) -> dict[tuple[int, int], set[tuple[int, int]]]:
        if self.last_roll is None:
            return {}
        a, b = self.last_roll
        player = self.current_player
        return {
            (a, b): self.board.legal_top_lefts(player, a, b),
            (b, a): self.board.legal_top_lefts(player, b, a),
        }

    def wildcard_value_is_legal(self, value: int) -> bool:
        a, b = self.last_roll
        if self.wildcard_index == 0:
            a = value
        else:
            b = value
        player = self.current_player
        return bool(self.board.legal_top_lefts(player, a, b) or self.board.legal_top_lefts(player, b, a))

    def attempt_place(self, top_left: tuple[int, int], w: int, h: int) -> bool:
        if self.state != TurnState.CHOOSING_PLACEMENT:
            return False
        legal_set = self.legal_cache.get((w, h))
        if legal_set is None or top_left not in legal_set:
            return False
        rect = self.board.place(self.current_player, top_left, w, h)
        captured = self.board.flag_cells.intersection(rect.cells())
        self.current_player.flags_captured += len(captured)
        self.current_player.consecutive_skips = 0
        self.history.append(
            TurnRecord(
                self.current_player_id,
                self.last_roll,
                placed=rect,
                wildcard_original_roll=self.wildcard_original_roll,
            )
        )
        return True

    def end_turn(self) -> None:
        if self.state == TurnState.GAME_OVER:
            return
        self.current_player_id = PLAYER_2 if self.current_player_id == PLAYER_1 else PLAYER_1
        self.last_roll = None
        self.wildcard_index = None
        self.wildcard_original_roll = None
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

    def total_score(self, player: Player) -> int:
        return player.total_area + player.flags_captured * self.flag_bonus_points

    def potential_stats(self, player: Player) -> dict[str, int]:
        reachable = self.board.reachable_empty_cells(player)
        return {
            "area": len(reachable),
            "flag_points": len(reachable & self.board.flag_cells) * self.flag_bonus_points,
        }

    def winner(self) -> int | None:
        if self.game_over_reason == GameOverReason.SURRENDER and self.surrendered_player_id is not None:
            return PLAYER_2 if self.surrendered_player_id == PLAYER_1 else PLAYER_1
        p1, p2 = self.players[PLAYER_1], self.players[PLAYER_2]
        if self.total_score(p1) > self.total_score(p2):
            return PLAYER_1
        if self.total_score(p2) > self.total_score(p1):
            return PLAYER_2
        return None
