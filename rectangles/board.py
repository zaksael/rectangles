from __future__ import annotations

from collections import deque

from .constants import BOARD_SIZE, OBSTACLE_OWNER
from .models import Player, Rectangle


class Board:
    def __init__(
        self,
        size: int = BOARD_SIZE,
        flag_cells: frozenset[tuple[int, int]] = frozenset(),
        wall_edges: frozenset[frozenset[tuple[int, int]]] = frozenset(),
        obstacle_cells: frozenset[tuple[int, int]] = frozenset(),
    ):
        self.size = size
        self.flag_cells = flag_cells
        self.wall_edges = wall_edges
        self.obstacle_cells = obstacle_cells
        self._grid: list[list[int | None]] = [[None] * size for _ in range(size)]
        for r, c in obstacle_cells:
            self._grid[r][c] = OBSTACLE_OWNER

    def set_obstacle_cells(self, cells: frozenset[tuple[int, int]]) -> None:
        # Unlike flag_cells/wall_edges (pure metadata a caller can safely
        # overwrite as a bare attribute), obstacle cells are baked into
        # _grid at construction time - persistence.py's load path needs
        # this to swap a freshly-reset Game's (wrong) rolled obstacles for
        # the saved ones without leaving the old sentinel cells stuck.
        for r, c in self.obstacle_cells:
            self._grid[r][c] = None
        self.obstacle_cells = cells
        for r, c in cells:
            self._grid[r][c] = OBSTACLE_OWNER

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def owner_at(self, r: int, c: int) -> int | None:
        return self._grid[r][c]

    def is_empty(self, r: int, c: int) -> bool:
        return self._grid[r][c] is None

    def is_edge_walled(self, a: tuple[int, int], b: tuple[int, int]) -> bool:
        return frozenset((a, b)) in self.wall_edges

    def _crosses_wall(self, r: int, c: int, w: int, h: int) -> bool:
        def inside(cell: tuple[int, int]) -> bool:
            cr, cc = cell
            return r <= cr < r + h and c <= cc < c + w

        return any(all(inside(cell) for cell in edge) for edge in self.wall_edges)

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

        # 3. The piece must not straddle a walled edge - a wall blocks
        # building across it even though every individual cell stays empty.
        if self._crosses_wall(r, c, w, h):
            return False

        if not player.has_moved:
            # 4. First placement must be anchored at the player's start corner.
            candidate = Rectangle(top_left=(r, c), width=w, height=h, owner=player.id)
            return candidate.top_left == player.start_corner or candidate.bottom_right == player.start_corner

        # 5. Every subsequent placement must be edge-adjacent to an owned
        # cell, not counting adjacency across a walled edge.
        for cc in range(c, c + w):
            if (
                self.in_bounds(r - 1, cc)
                and self.owner_at(r - 1, cc) == player.id
                and not self.is_edge_walled((r - 1, cc), (r, cc))
            ):
                return True
            if (
                self.in_bounds(r + h, cc)
                and self.owner_at(r + h, cc) == player.id
                and not self.is_edge_walled((r + h - 1, cc), (r + h, cc))
            ):
                return True
        for cr in range(r, r + h):
            if (
                self.in_bounds(cr, c - 1)
                and self.owner_at(cr, c - 1) == player.id
                and not self.is_edge_walled((cr, c - 1), (cr, c))
            ):
                return True
            if (
                self.in_bounds(cr, c + w)
                and self.owner_at(cr, c + w) == player.id
                and not self.is_edge_walled((cr, c + w - 1), (cr, c + w))
            ):
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
                    if (
                        self.in_bounds(nr, nc)
                        and self._grid[nr][nc] is None
                        and not self.is_edge_walled((r, c), (nr, nc))
                    ):
                        result.add((nr, nc))
        return result

    def reachable_empty_cells(self, player: Player) -> set[tuple[int, int]]:
        if player.has_moved:
            seeds = self.frontier(player)
        elif self.is_empty(*player.start_corner):
            seeds = {player.start_corner}
        else:
            seeds = set()

        visited = set(seeds)
        queue = deque(seeds)
        while queue:
            r, c = queue.popleft()
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if (nr, nc) in visited or not self.in_bounds(nr, nc):
                    continue
                if self._grid[nr][nc] is not None or self.is_edge_walled((r, c), (nr, nc)):
                    continue
                visited.add((nr, nc))
                queue.append((nr, nc))
        return visited

    def self_enclosed_cell_counts(self) -> dict[int, int]:
        # A connected empty region bordered (ignoring wall-blocked edges)
        # by exactly one player's cells is "self-enclosed" for that player -
        # unless it also touches the board's outer edge, in which case it's
        # never penalized: the board edge did part of the enclosing for
        # free, so it isn't a gap the player actually closed off themselves.
        # Obstacle cells contribute no owner (same as a wall) - they don't
        # make a region "shared" or "unowned" any differently than an
        # ordinary boundary would.
        counts: dict[int, int] = {}
        visited: set[tuple[int, int]] = set()
        for r in range(self.size):
            for c in range(self.size):
                if (r, c) in visited or self._grid[r][c] is not None:
                    continue
                region: list[tuple[int, int]] = []
                owners: set[int] = set()
                touches_edge = False
                queue = deque([(r, c)])
                visited.add((r, c))
                while queue:
                    cr, cc = queue.popleft()
                    region.append((cr, cc))
                    for nr, nc in ((cr - 1, cc), (cr + 1, cc), (cr, cc - 1), (cr, cc + 1)):
                        if not self.in_bounds(nr, nc):
                            touches_edge = True
                            continue
                        if self.is_edge_walled((cr, cc), (nr, nc)):
                            continue
                        owner = self._grid[nr][nc]
                        if owner is None:
                            if (nr, nc) not in visited:
                                visited.add((nr, nc))
                                queue.append((nr, nc))
                        elif owner != OBSTACLE_OWNER:
                            owners.add(owner)
                if not touches_edge and len(owners) == 1:
                    owner = next(iter(owners))
                    counts[owner] = counts.get(owner, 0) + len(region)
        return counts

    def self_enclosed_count_if(self, player_id: int, top_left: tuple[int, int], w: int, h: int) -> int:
        # What-if variant of self_enclosed_cell_counts(), for scoring a
        # hypothetical placement (replay analysis) without mutating real
        # game state: stamps the grid directly rather than going through
        # place() (no Rectangle/Player.pieces bookkeeping needed), computes,
        # then reverts. Caller must pass cells that are actually empty
        # (true for every legal candidate) so the revert-to-None is exact.
        r, c = top_left
        for cr in range(r, r + h):
            for cc in range(c, c + w):
                self._grid[cr][cc] = player_id
        try:
            return self.self_enclosed_cell_counts().get(player_id, 0)
        finally:
            for cr in range(r, r + h):
                for cc in range(c, c + w):
                    self._grid[cr][cc] = None

    def legal_top_lefts(self, player: Player, w: int, h: int) -> set[tuple[int, int]]:
        result: set[tuple[int, int]] = set()
        for r in range(self.size - h + 1):
            for c in range(self.size - w + 1):
                if self.can_place(player, (r, c), w, h):
                    result.add((r, c))
        return result
