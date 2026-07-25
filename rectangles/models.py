from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True)
class Rectangle:
    top_left: tuple[int, int]  # (row, col)
    width: int
    height: int
    owner: int

    @property
    def area(self) -> int:
        return self.width * self.height

    @property
    def bottom_right(self) -> tuple[int, int]:
        r0, c0 = self.top_left
        return (r0 + self.height - 1, c0 + self.width - 1)

    def cells(self) -> Iterator[tuple[int, int]]:
        r0, c0 = self.top_left
        for r in range(r0, r0 + self.height):
            for c in range(c0, c0 + self.width):
                yield (r, c)


@dataclass
class Player:
    id: int
    name: str
    start_corner: tuple[int, int]
    pieces: list[Rectangle] = field(default_factory=list)

    @property
    def total_area(self) -> int:
        return sum(p.area for p in self.pieces)

    @property
    def has_moved(self) -> bool:
        return len(self.pieces) > 0
