from __future__ import annotations

import math
import random
from enum import Enum, auto

from .board import Board
from .constants import (
    BOARD_SIZE,
    COMEBACK_NUDGE_ENABLED,
    COMEBACK_NUDGE_EXTRA_REROLLS,
    COMEBACK_NUDGE_THRESHOLD_FRACTION,
    DICE_MAX,
    DICE_MIN,
    PRIZE_CELL_PAIRS,
    PRIZE_ENABLED,
    MIN_SPECIAL_CELL_DISTANCE,
    PITFALL_CELL_PAIRS,
    PITFALL_ENABLED,
    OBSTACLE_CELL_PAIRS,
    OBSTACLES_ENABLED,
    PLAYER_1,
    PLAYER_2,
    PLAYER_NAMES,
    REROLL_ENABLED,
    REROLL_LIMIT,
    SELF_ENCLOSED_PENALTY_ENABLED,
    SELF_ENCLOSED_PENALTY_PER_CELL,
    SKIP_LIMIT,
    SPECIAL_CELL_KINDS,
    START_CORNER_EXCLUSION_RADIUS,
    WALL_LINE_LENGTH,
    WALL_LINE_PAIRS,
    WALLS_ENABLED,
    WILDCARD_ENABLED,
    CellEffect,
    CellKind,
)
from .models import Cell, Player, SpecialCell, TurnRecord


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


def _near_any(cell: tuple[int, int], others: set[tuple[int, int]]) -> bool:
    r, c = cell
    return any(max(abs(r - pr), abs(c - pc)) < MIN_SPECIAL_CELL_DISTANCE for pr, pc in others)


class Game:
    def __init__(
        self,
        board_size: int = BOARD_SIZE,
        skip_limit: int = SKIP_LIMIT,
        prize_enabled: bool = PRIZE_ENABLED,
        walls_enabled: bool = WALLS_ENABLED,
        obstacles_enabled: bool = OBSTACLES_ENABLED,
        pitfall_enabled: bool = PITFALL_ENABLED,
        special_cell_points: dict[str, int] | None = None,
        wildcard_enabled: bool = WILDCARD_ENABLED,
        self_enclosed_penalty_enabled: bool = SELF_ENCLOSED_PENALTY_ENABLED,
        reroll_enabled: bool = REROLL_ENABLED,
        comeback_nudge_enabled: bool = COMEBACK_NUDGE_ENABLED,
        rng: random.Random | None = None,
    ):
        self.board_size = board_size
        self.skip_limit = skip_limit
        self.prize_enabled = prize_enabled
        self.walls_enabled = walls_enabled
        self.obstacles_enabled = obstacles_enabled
        self.pitfall_enabled = pitfall_enabled
        self.special_cell_points = dict(special_cell_points or {})
        self.wildcard_enabled = wildcard_enabled
        self.self_enclosed_penalty_enabled = self_enclosed_penalty_enabled
        self.reroll_enabled = reroll_enabled
        self.comeback_nudge_enabled = comeback_nudge_enabled
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
        prize_cells = self._prize_cells() if self.prize_enabled else frozenset()
        wall_edges = self._wall_edges(prize_cells) if self.walls_enabled else frozenset()
        obstacle_cells = (
            self._obstacle_cells(prize_cells, wall_edges) if self.obstacles_enabled else frozenset()
        )
        pitfall_cells = (
            self._pitfall_cells(prize_cells, wall_edges, obstacle_cells)
            if self.pitfall_enabled
            else frozenset()
        )
        special_cells: set[SpecialCell] = set()
        pair_id = 0
        for kind, cells in ((CellKind.PRIZE, prize_cells), (CellKind.PITFALL, pitfall_cells)):
            for r, c in cells:
                special_cells.add(SpecialCell(kind, Cell(r, c), pair_id))
                pair_id += 1
        self.board = Board(
            self.board_size,
            special_cells=frozenset(special_cells),
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

    def _mirrored_cell_pairs(
        self,
        count: int,
        occupied: set[tuple[int, int]],
    ) -> frozenset[tuple[int, int]]:
        """Shared by Prize/Obstacles: `count` mirrored single-cell
        pairs, enumerate-then-pick from candidates outside `occupied`, the
        start-corner exclusion zone, MIN_SPECIAL_CELL_DISTANCE of any pair
        already placed *by this call* (so a feature's own pairs spread out -
        `occupied` itself, e.g. another feature's cells, gets no such
        buffer), and MIN_SPECIAL_CELL_DISTANCE of the candidate's own mirror
        (near the board's center, a cell can otherwise end up right next to
        its own mirror partner - a degenerate un-spread-out "pair"). A pair
        with an empty candidate pool is skipped, not errored (fewer cells
        seeded that game)."""
        size = self.board_size
        occupied = set(occupied)
        own_picked: set[tuple[int, int]] = set()
        result: set[tuple[int, int]] = set()

        for _ in range(count):
            candidates = [
                (r, c)
                for r in range(size)
                for c in range(size)
                if (r, c) not in occupied
                and not _near_start_corner((r, c), size)
                and not _near_any((r, c), {_mirror_cell((r, c), size)})
                and not _near_any((r, c), own_picked)
            ]
            if not candidates:
                continue
            cell = candidates[self.rng.randint(0, len(candidates) - 1)]
            mirrored = _mirror_cell(cell, size)
            occupied.add(cell)
            occupied.add(mirrored)
            own_picked.add(cell)
            own_picked.add(mirrored)
            result.add(cell)
            result.add(mirrored)

        return frozenset(result)

    def _prize_cells(self) -> frozenset[tuple[int, int]]:
        return self._mirrored_cell_pairs(PRIZE_CELL_PAIRS, set())

    def _wall_edges(
        self, prize_cells: frozenset[tuple[int, int]]
    ) -> frozenset[frozenset[tuple[int, int]]]:
        size = self.board_size

        def segment_edges(
            horizontal: bool, fixed: int, start: int
        ) -> list[frozenset[tuple[int, int]]]:
            if horizontal:
                return [frozenset({(fixed, i), (fixed + 1, i)}) for i in range(start, start + WALL_LINE_LENGTH)]
            return [frozenset({(i, fixed), (i, fixed + 1)}) for i in range(start, start + WALL_LINE_LENGTH)]

        occupied: set[tuple[int, int]] = set(prize_cells)
        own_placed: set[tuple[int, int]] = set()
        result: set[frozenset[tuple[int, int]]] = set()

        for _ in range(WALL_LINE_PAIRS):
            horizontal = self.rng.randint(0, 1) == 0
            candidates: list[list[frozenset[tuple[int, int]]]] = []
            for fixed in range(size - 1):
                for start in range(size - WALL_LINE_LENGTH + 1):
                    edges = segment_edges(horizontal, fixed, start)
                    cells = set().union(*edges)
                    mirrored_cells = {_mirror_cell(cell, size) for cell in cells}
                    if any(_near_any(cell, mirrored_cells) for cell in cells):
                        # too close to (or overlapping) its own mirror image -
                        # near the center, that's a degenerate un-spread pair.
                        continue
                    if any(_near_start_corner(cell, size) for cell in cells) or cells & occupied:
                        continue
                    if any(_near_any(cell, own_placed) for cell in cells):
                        continue
                    candidates.append(edges)
            if not candidates:
                continue
            edges = candidates[self.rng.randint(0, len(candidates) - 1)]
            mirrored_edges = [frozenset(_mirror_cell(c, size) for c in edge) for edge in edges]
            placed = set().union(*edges, *mirrored_edges)
            occupied |= placed
            own_placed |= placed
            result.update(edges)
            result.update(mirrored_edges)

        return frozenset(result)

    def _obstacle_cells(
        self,
        prize_cells: frozenset[tuple[int, int]],
        wall_edges: frozenset[frozenset[tuple[int, int]]],
    ) -> frozenset[tuple[int, int]]:
        occupied = set(prize_cells) | {cell for edge in wall_edges for cell in edge}
        return self._mirrored_cell_pairs(OBSTACLE_CELL_PAIRS, occupied)

    def _pitfall_cells(
        self,
        prize_cells: frozenset[tuple[int, int]],
        wall_edges: frozenset[frozenset[tuple[int, int]]],
        obstacle_cells: frozenset[tuple[int, int]],
    ) -> frozenset[tuple[int, int]]:
        occupied = set(prize_cells) | {cell for edge in wall_edges for cell in edge} | set(obstacle_cells)
        return self._mirrored_cell_pairs(PITFALL_CELL_PAIRS, occupied)

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
            if any(self.wildcard_value_is_legal(v) for v in range(DICE_MIN, DICE_MAX + 1)):
                self.state = TurnState.CHOOSING_WILDCARD
                return self.last_roll
            # No wildcard value would produce a legal placement either -
            # forcing the player through a picker where every option is
            # illegal is a pointless extra click, so resolve straight into
            # the skip it would have ended in anyway. wildcard_original_roll
            # stays set so the skip's history entry still records it as a
            # wildcard roll.
            self.wildcard_index = None

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
            # Defer committing the skip while a reroll charge could still be
            # spent instead - nothing should be recorded until the player's
            # final choice, same principle CHOOSING_PLACEMENT/CHOOSING_WILDCARD
            # already follow (attempt_place()/choose_wildcard_value() are the
            # only things that ever commit anything there).
            if not self.can_reroll():
                self._commit_skip()

    def _commit_skip(self) -> None:
        self.current_player.consecutive_skips += 1
        self.history.append(
            TurnRecord(
                self.current_player_id,
                self.last_roll,
                placed=None,
                wildcard_original_roll=self.wildcard_original_roll,
            )
        )

    def confirm_skip(self) -> None:
        if self.state != TurnState.SKIPPED:
            raise ValueError(f"Cannot confirm a skip in state {self.state}")
        if self.can_reroll():
            self._commit_skip()

    @property
    def comeback_nudge_threshold(self) -> int:
        return math.ceil(self.board_size**2 * COMEBACK_NUDGE_THRESHOLD_FRACTION)

    def effective_reroll_limit(self, player: Player) -> int:
        if self.comeback_nudge_enabled and player.comeback_nudge_granted:
            return REROLL_LIMIT + COMEBACK_NUDGE_EXTRA_REROLLS
        return REROLL_LIMIT

    def can_reroll(self) -> bool:
        player = self.current_player
        if self.reroll_enabled and player.rerolls_used < REROLL_LIMIT:
            return True
        return (
            self.comeback_nudge_enabled
            and player.comeback_nudge_granted
            and player.rerolls_used < self.effective_reroll_limit(player)
        )

    def reroll(self) -> None:
        if self.state not in (
            TurnState.CHOOSING_WILDCARD,
            TurnState.CHOOSING_PLACEMENT,
            TurnState.SKIPPED,
        ):
            raise ValueError(f"Cannot reroll in state {self.state}")
        if not self.can_reroll():
            raise ValueError("No reroll charges available")

        self.current_player.rerolls_used += 1
        self.wildcard_index = None
        self.wildcard_original_roll = None
        self.legal_cache = {}
        self.state = TurnState.AWAITING_ROLL
        self.roll_dice()

    def legal_placements_for_roll(self) -> dict[tuple[int, int], set[tuple[int, int]]]:
        if self.last_roll is None:
            return {}
        a, b = self.last_roll
        player = self.current_player
        return {
            (a, b): self.board.legal_top_lefts(player, a, b),
            (b, a): self.board.legal_top_lefts(player, b, a),
        }

    def legal_placements_for_value(self, value: int) -> dict[tuple[int, int], set[tuple[int, int]]]:
        a, b = self.last_roll
        if self.wildcard_index == 0:
            a = value
        else:
            b = value
        player = self.current_player
        return {
            (a, b): self.board.legal_top_lefts(player, a, b),
            (b, a): self.board.legal_top_lefts(player, b, a),
        }

    def wildcard_value_is_legal(self, value: int) -> bool:
        return any(self.legal_placements_for_value(value).values())

    def attempt_place(self, top_left: tuple[int, int], w: int, h: int) -> bool:
        if self.state != TurnState.CHOOSING_PLACEMENT:
            return False
        legal_set = self.legal_cache.get((w, h))
        if legal_set is None or top_left not in legal_set:
            return False
        rect = self.board.place(self.current_player, top_left, w, h)
        placed = set(rect.cells())
        for sc in self.board.special_cells:
            if sc.location in placed:
                captures = self.current_player.special_captures
                captures[sc.kind] = captures.get(sc.kind, 0) + 1
        self.current_player.consecutive_skips = 0
        self.history.append(
            TurnRecord(
                self.current_player_id,
                self.last_roll,
                placed=rect,
                wildcard_original_roll=self.wildcard_original_roll,
            )
        )
        self._maybe_grant_comeback_nudge()
        return True

    def _maybe_grant_comeback_nudge(self) -> None:
        if not self.comeback_nudge_enabled:
            return
        p1, p2 = self.players[PLAYER_1], self.players[PLAYER_2]
        trailing, leading = (p1, p2) if self.total_score(p1) < self.total_score(p2) else (p2, p1)
        if (
            not trailing.comeback_nudge_granted
            and self.total_score(leading) - self.total_score(trailing) >= self.comeback_nudge_threshold
        ):
            trailing.comeback_nudge_granted = True

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

    def points_for(self, kind: CellKind) -> int:
        base = SPECIAL_CELL_KINDS[kind]
        return self.special_cell_points.get(kind.value, base.points)

    def _other_player(self, player: Player) -> Player:
        other_id = PLAYER_2 if player.id == PLAYER_1 else PLAYER_1
        return self.players[other_id]

    def total_score(self, player: Player) -> int:
        other = self._other_player(player)
        score = player.total_area
        for kind, effect in SPECIAL_CELL_KINDS.items():
            points = self.points_for(kind)
            score += effect.capturer_sign * player.special_captures.get(kind, 0) * points
            score += effect.opponent_sign * other.special_captures.get(kind, 0) * points
        if self.self_enclosed_penalty_enabled:
            penalty = self.board.self_enclosed_cell_counts().get(player.id, 0)
            score -= penalty * SELF_ENCLOSED_PENALTY_PER_CELL
        return score

    def potential_stats(self, player: Player) -> dict[str, int]:
        reachable = self.board.reachable_empty_cells(player)
        return {
            "area": len(reachable),
            "prize_points": len(reachable & self.board.cells_of_kind(CellKind.PRIZE)) * self.points_for(CellKind.PRIZE),
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
