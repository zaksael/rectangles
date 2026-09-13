from __future__ import annotations

import pygame

from ...engine.game import Game, TurnState
from ...engine.series import Series
from ...engine.tournament import Bracket
from . import colors
from .. import layout
from .board import BoardMixin
from .dialogs import DialogsMixin
from .mode_select import ModeSelectMixin
from .panel import PanelMixin
from .replay import ReplayMixin, _AnalysisCandidate
from .settings import SettingsMixin
from .tournament import TournamentMixin
from ..state import Screen, UIState


class Renderer(BoardMixin, PanelMixin, ModeSelectMixin, SettingsMixin, ReplayMixin, TournamentMixin, DialogsMixin):
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # Everything is drawn onto this fixed-size canvas, then draw() scales
        # it to fit the real, freely-resizable window.
        self._canvas = pygame.Surface((layout.DESIGN_WIDTH, layout.DESIGN_HEIGHT))
        # Full-height surface the (possibly taller-than-canvas) settings screen
        # is drawn onto and scrolled into view. Allocated once before any mode
        # is chosen, so sized for the tallest mode - see SETTINGS_CONTENT_HEIGHT_MAX.
        self._settings_surface = pygame.Surface((layout.DESIGN_WIDTH, layout.SETTINGS_CONTENT_HEIGHT_MAX))
        _FONT_STACK = "segoeui,helveticaneue,helvetica,arial"
        self.font = pygame.font.SysFont(_FONT_STACK, 19)
        self.font_small = pygame.font.SysFont(_FONT_STACK, 15)
        self.font_big = pygame.font.SysFont(_FONT_STACK, 29, bold=True)
        self.font_dice = pygame.font.SysFont(_FONT_STACK, 28, bold=True)
        self._hand_cursor = False
        self._mouse_pos = (0, 0)
        self._turn_analyses_cache: tuple[Game, int, dict[int, tuple[str, _AnalysisCandidate]]] | None = None

    def resize(self, screen: pygame.Surface) -> None:
        self.screen = screen

    def draw(
        self,
        game: Game | None,
        ui_state: UIState,
        series: Series | None = None,
        tournament: Bracket | None = None,
    ) -> None:
        real_width, real_height = self.screen.get_size()
        self._mouse_pos = layout.to_design_coords(*pygame.mouse.get_pos(), real_width, real_height)

        real_screen, self.screen = self.screen, self._canvas
        self.screen.fill(colors.BG_COLOR)
        self._hand_cursor = False
        if ui_state.screen == Screen.MODE_SELECT:
            self._draw_mode_select_screen(ui_state)
        elif ui_state.screen == Screen.SETTINGS:
            self._settings_surface.fill(colors.BG_COLOR)
            canvas, self.screen = self.screen, self._settings_surface
            self._draw_settings_screen(ui_state)
            self.screen = canvas
            visible = pygame.Rect(0, ui_state.settings_scroll, layout.DESIGN_WIDTH, layout.DESIGN_HEIGHT)
            self.screen.blit(self._settings_surface, (0, 0), area=visible)
            if ui_state.settings_scroll < layout.settings_max_scroll(ui_state.selected_game_mode, ui_state.tournament_size):
                # Mask the strip first: it can sit over clipped content, not blank space.
                strip = pygame.Rect(0, layout.DESIGN_HEIGHT - 26, layout.DESIGN_WIDTH, 26)
                self.screen.fill(colors.BG_COLOR, strip)
                hint = self.font_small.render("scroll for more ▼", True, colors.MUTED_TEXT_COLOR)
                self.screen.blit(
                    hint, hint.get_rect(center=(layout.DESIGN_WIDTH // 2, layout.DESIGN_HEIGHT - 14))
                )
        elif ui_state.screen == Screen.REPLAY:
            self._draw_replay(game, ui_state)
        elif ui_state.screen == Screen.TOURNAMENT:
            self._draw_tournament(tournament)
        else:
            self._draw_board(game)
            if game.state == TurnState.CHOOSING_PLACEMENT:
                self._draw_coverable_cells(game, ui_state)
                if ui_state.hover_top_left is not None:
                    self._draw_ghost(ui_state, game.board.size)
            self._draw_status_banner(game)
            self._draw_panel(game, ui_state, series, tournament)
            if game.state == TurnState.GAME_OVER:
                self._draw_game_over(game, series, tournament)
            if ui_state.pending_confirmation is not None:
                self._draw_confirm_dialog(game, ui_state)
        try:
            pygame.mouse.set_cursor(
                pygame.SYSTEM_CURSOR_HAND if self._hand_cursor else pygame.SYSTEM_CURSOR_ARROW
            )
        except pygame.error:
            pass  # no real cursor to set under a headless/dummy video driver

        self.screen = real_screen
        scale, offset_x, offset_y = layout.compute_scale(real_width, real_height)
        self.screen.fill(colors.LETTERBOX_COLOR)
        scaled_size = (round(layout.DESIGN_WIDTH * scale), round(layout.DESIGN_HEIGHT * scale))
        scaled_canvas = pygame.transform.smoothscale(self._canvas, scaled_size)
        self.screen.blit(scaled_canvas, (offset_x, offset_y))
        pygame.display.flip()

    def _button(
        self,
        rect: pygame.Rect,
        label: str,
        enabled: bool = True,
        selected: bool = False,
        hovered: bool = False,
        outline: bool = False,
    ) -> None:
        """outline=True is the "chip" style for a selection group: neutral/
        bordered until hovered or selected. outline=False (default) is the
        solid-accent primary-action style (Start, Roll, ...)."""
        if enabled and rect.collidepoint(self._mouse_pos):
            self._hand_cursor = True
        border_color = None
        if not enabled:
            bg = colors.BUTTON_DISABLED_COLOR
            text_color = colors.BUTTON_DISABLED_TEXT_COLOR
        elif selected:
            bg = colors.BUTTON_SELECTED_COLOR
            text_color = colors.BUTTON_TEXT_COLOR
        elif outline:
            bg = colors.BUTTON_OUTLINE_HOVER_BG_COLOR if hovered else colors.BUTTON_OUTLINE_BG_COLOR
            text_color = colors.BUTTON_COLOR if hovered else colors.BUTTON_OUTLINE_TEXT_COLOR
            border_color = colors.BUTTON_COLOR if hovered else colors.BUTTON_OUTLINE_BORDER_COLOR
        else:
            bg = colors.BUTTON_HOVER_COLOR if hovered else colors.BUTTON_COLOR
            text_color = colors.BUTTON_TEXT_COLOR
        pygame.draw.rect(self.screen, bg, rect, border_radius=8)
        if border_color is not None:
            pygame.draw.rect(self.screen, border_color, rect, width=1, border_radius=8)
        text = self.font.render(label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_card(self, rect: pygame.Rect, radius: int = 12, shadow: bool = True) -> None:
        """A white, softly-shadowed "elevated card" panel."""
        if shadow:
            shadow_surf = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, colors.CARD_SHADOW_COLOR, shadow_surf.get_rect(), border_radius=radius + 2)
            self.screen.blit(shadow_surf, (rect.x - 4, rect.y - 1))
        pygame.draw.rect(self.screen, colors.CARD_BG_COLOR, rect, border_radius=radius)
        pygame.draw.rect(self.screen, colors.CARD_BORDER_COLOR, rect, width=1, border_radius=radius)

    def _text(self, text: str, pos: tuple[int, int], font=None, color=colors.TEXT_COLOR) -> None:
        font = font or self.font
        self.screen.blit(font.render(text, True, color), pos)

    def _wrap_text(self, text: str, font, max_width: int) -> list[str]:
        words = text.split(" ")
        lines = [words[0]]
        for word in words[1:]:
            candidate = f"{lines[-1]} {word}"
            if font.size(candidate)[0] <= max_width:
                lines[-1] = candidate
            else:
                lines.append(word)
        return lines

    def _draw_wrapped_text(
        self, text: str, pos: tuple[int, int], font, max_width: int, color: tuple[int, int, int] = colors.TEXT_COLOR
    ) -> int:
        x, y = pos
        for line in self._wrap_text(text, font, max_width):
            self._text(line, (x, y), font, color)
            y += font.get_linesize()
        return y

    def _divider(self, y: int) -> None:
        pygame.draw.line(
            self.screen, colors.DIVIDER_COLOR, (layout.PANEL_X, y), (layout.PANEL_X + layout.PANEL_CONTENT_WIDTH, y)
        )
