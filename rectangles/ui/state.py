from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UIState:
    current_dims: tuple[int, int] | None = None
    hover_top_left: tuple[int, int] | None = None
    hover_legal: bool = False

    def reset(self) -> None:
        self.current_dims = None
        self.hover_top_left = None
        self.hover_legal = False
