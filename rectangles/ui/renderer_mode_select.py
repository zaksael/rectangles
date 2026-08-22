from __future__ import annotations

import pygame

from .. import persistence
from . import layout
from .colors import MUTED_TEXT_COLOR, TEXT_COLOR
from .state import UIState


class ModeSelectMixin:
    def _draw_mode_select_screen(self, ui_state: UIState) -> None:
        center_x = layout.DESIGN_WIDTH // 2
        mouse_pos = self._mouse_pos

        def hovered(rect: pygame.Rect) -> bool:
            return rect.collidepoint(mouse_pos)

        title_surf = self.font_big.render("RECTANGLES", True, TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(center_x, 56)))
        subtitle_surf = self.font.render("Choose a game mode", True, MUTED_TEXT_COLOR)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(center_x, 96)))

        for mode, rect in layout.MODE_SELECT_BUTTON_RECTS.items():
            self._button(
                rect,
                mode,
                hovered=hovered(rect),
                outline=True,
            )

        if persistence.has_save():
            self._button(
                layout.MODE_SELECT_RESUME_BUTTON_RECT,
                "Resume Game (R)",
                hovered=hovered(layout.MODE_SELECT_RESUME_BUTTON_RECT),
                outline=True,
            )
        self._button(
            layout.MODE_SELECT_EXIT_BUTTON_RECT,
            "Exit (Esc)",
            hovered=hovered(layout.MODE_SELECT_EXIT_BUTTON_RECT),
            outline=True,
        )
