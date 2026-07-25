from __future__ import annotations

from .constants import BOARD_SIZE
from .models import Player, Rectangle


class Board:
    def __init__(self, size: int = BOARD_SIZE):
        self.size = size
        self._grid: list[list[int | None]] = [[None] * size for _ in range(size)]

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def owner_at(self, r: int, c: int) -> int | None:
        return self._grid[r][c]

    def is_empty(self, r: int, c: int) -> bool:
        return self._grid[r][c] is None

    def can_place(self, player: Player, top_left: tuple[int, int], w: int, h: int) -> bool:
        r, c = top_left

        # 1. Bounds.
        if r < 0 or c < 0 or r + h > self.size or c + w > self.size:
            return False

        # 2. All covered cells must be empty.
        for cr in range(r, r + h):
            for cc in range(c, c + w):
                if self._grid[cr][cc] is not None:
                    return False

        if not player.has_moved:
            # 3. First placement must be anchored at the player's start corner.
            candidate = Rectangle(top_left=(r, c), width=w, height=h, owner=player.id)
            return candidate.top_left == player.start_corner or candidate.bottom_right == player.start_corner

        # 4. Every subsequent placement must be edge-adjacent to an owned cell.
        for cc in range(c, c + w):
            if self.in_bounds(r - 1, cc) and self.owner_at(r - 1, cc) == player.id:
                return True
            if self.in_bounds(r + h, cc) and self.owner_at(r + h, cc) == player.id:
                return True
        for cr in range(r, r + h):
            if self.in_bounds(cr, c - 1) and self.owner_at(cr, c - 1) == player.id:
                return True
            if self.in_bounds(cr, c + w) and self.owner_at(cr, c + w) == player.id:
                return True
        return False

    def place(self, player: Player, top_left: tuple[int, int], w: int, h: int) -> Rectangle:
        rect = Rectangle(top_left=top_left, width=w, height=h, owner=player.id)
        r, c = top_left
        for cr in range(r, r + h):
            for cc in range(c, c + w):
                self._grid[cr][cc] = player.id
        player.pieces.append(rect)
        return rect

    def frontier(self, player: Player) -> set[tuple[int, int]]:
        result: set[tuple[int, int]] = set()
        for r in range(self.size):
            for c in range(self.size):
                if self._grid[r][c] != player.id:
                    continue
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if self.in_bounds(nr, nc) and self._grid[nr][nc] is None:
                        result.add((nr, nc))
        return result

    def legal_top_lefts(self, player: Player, w: int, h: int) -> set[tuple[int, int]]:
        result: set[tuple[int, int]] = set()
        for r in range(self.size - h + 1):
            for c in range(self.size - w + 1):
                if self.can_place(player, (r, c), w, h):
                    result.add((r, c))
        return result
