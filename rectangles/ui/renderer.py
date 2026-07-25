from __future__ import annotations

import pygame

from .. import constants
from ..game import Game, GameOverReason, TurnState
from . import layout
from .state import Screen, UIState

BG_COLOR = (245, 245, 245)
GRID_LINE_COLOR = (205, 205, 205)
EMPTY_CELL_COLOR = (255, 255, 255)
PANEL_BG_COLOR = (228, 228, 235)
TEXT_COLOR = (30, 30, 30)
MUTED_TEXT_COLOR = (110, 110, 110)
GHOST_LEGAL_COLOR = (80, 200, 120, 150)
GHOST_ILLEGAL_COLOR = (220, 70, 70, 130)
COVERABLE_CELL_COLOR = (190, 235, 200, 130)
BUTTON_COLOR = (90, 100, 210)
BUTTON_HOVER_COLOR = (110, 120, 230)
BUTTON_DISABLED_COLOR = (190, 190, 198)
BUTTON_SELECTED_COLOR = (70, 170, 100)
BUTTON_TEXT_COLOR = (255, 255, 255)
OVERLAY_COLOR = (15, 15, 20, 190)
DIVIDER_COLOR = (200, 200, 208)
ROW_ACTIVE_BG_COLOR = (205, 230, 214)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 20)
        self.font_small = pygame.font.SysFont("arial", 15)
        self.font_big = pygame.font.SysFont("arial", 30, bold=True)
        self.font_dice = pygame.font.SysFont("arial", 28, bold=True)

    def draw(self, game: Game | None, ui_state: UIState) -> None:
        self.screen.fill(BG_COLOR)
        if ui_state.screen == Screen.SETTINGS:
            self._draw_settings_screen(ui_state)
        else:
            self._draw_board(game)
            if game.state == TurnState.CHOOSING_PLACEMENT:
                self._draw_coverable_cells(game, ui_state)
                if ui_state.hover_top_left is not None:
                    self._draw_ghost(ui_state)
            self._draw_panel(game, ui_state)
            if game.state == TurnState.GAME_OVER:
                self._draw_game_over(game)
        pygame.display.flip()

    def _draw_settings_screen(self, ui_state: UIState) -> None:
        center_x = layout.WINDOW_WIDTH // 2

        title_surf = self.font_big.render("RECTANGLES", True, TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(center_x, 80)))
        subtitle_surf = self.font.render("Choose your settings", True, MUTED_TEXT_COLOR)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(center_x, 130)))

        board_label = self.font.render("Board size", True, TEXT_COLOR)
        self.screen.blit(board_label, board_label.get_rect(center=(center_x, 230)))
        for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
            self._button(rect, f"{value}x{value}", selected=value == ui_state.selected_board_size)

        skip_label = self.font.render("Skip limit", True, TEXT_COLOR)
        self.screen.blit(skip_label, skip_label.get_rect(center=(center_x, 370)))
        for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
            self._button(rect, str(value), selected=value == ui_state.selected_skip_limit)

        self._button(layout.SETTINGS_START_BUTTON_RECT, "Start Game (Space)")
        self._button(layout.SETTINGS_EXIT_BUTTON_RECT, "Exit (Esc)")

    def _draw_board(self, game: Game) -> None:
        for r in range(game.board.size):
            for c in range(game.board.size):
                rect = layout.cell_rect(r, c)
                pygame.draw.rect(self.screen, EMPTY_CELL_COLOR, rect)
                pygame.draw.rect(self.screen, GRID_LINE_COLOR, rect, width=1)

        for player in game.players.values():
            color = constants.PLAYER_COLORS[player.id]
            border = constants.PLAYER_BORDER_COLORS[player.id]
            for piece in player.pieces:
                rect = layout.piece_rect(piece.top_left, piece.width, piece.height)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, border, rect, width=3)

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

    def _draw_coverable_cells(self, game: Game, ui_state: UIState) -> None:
        if ui_state.current_dims is None:
            return
        w, h = ui_state.current_dims
        legal_top_lefts = game.legal_cache.get((w, h), set())
        if not legal_top_lefts:
            return

        covered: set[tuple[int, int]] = set()
        for r0, c0 in legal_top_lefts:
            for r in range(r0, r0 + h):
                for c in range(c0, c0 + w):
                    covered.add((r, c))

        overlay = pygame.Surface((layout.CELL_PX, layout.CELL_PX), pygame.SRCALPHA)
        overlay.fill(COVERABLE_CELL_COLOR)
        for r, c in covered:
            self.screen.blit(overlay, layout.cell_rect(r, c).topleft)

    def _draw_ghost(self, ui_state: UIState) -> None:
        w, h = ui_state.current_dims
        rect = layout.piece_rect(ui_state.hover_top_left, w, h)
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill(GHOST_LEGAL_COLOR if ui_state.hover_legal else GHOST_ILLEGAL_COLOR)
        self.screen.blit(overlay, rect.topleft)
        pygame.draw.rect(self.screen, (30, 30, 30), rect, width=2)

    def _button(self, rect: pygame.Rect, label: str, enabled: bool = True, selected: bool = False) -> None:
        if selected:
            color = BUTTON_SELECTED_COLOR
        elif enabled:
            color = BUTTON_COLOR
        else:
            color = BUTTON_DISABLED_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        if selected:
            pygame.draw.rect(self.screen, (255, 255, 255), rect, width=3, border_radius=6)
        text = self.font.render(label, True, BUTTON_TEXT_COLOR)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _text(self, text: str, pos: tuple[int, int], font=None, color=TEXT_COLOR) -> None:
        font = font or self.font
        self.screen.blit(font.render(text, True, color), pos)

    def _divider(self, y: int) -> None:
        pygame.draw.line(
            self.screen, DIVIDER_COLOR, (layout.PANEL_X, y), (layout.PANEL_X + layout.PANEL_CONTENT_WIDTH, y)
        )

    def _draw_panel(self, game: Game, ui_state: UIState) -> None:
        pygame.draw.rect(self.screen, PANEL_BG_COLOR, layout.PANEL_RECT)
        x = layout.PANEL_X

        self._text("RECTANGLES", (x, layout.PANEL_HEADER_Y), self.font_big)
        self._divider(layout.PANEL_DIVIDER_1_Y)

        y = layout.PANEL_SCORE_Y
        for player in game.players.values():
            active = player.id == game.current_player_id and game.state != TurnState.GAME_OVER
            if active:
                row_rect = pygame.Rect(
                    x - 8, y - 4, layout.PANEL_CONTENT_WIDTH + 16, layout.PANEL_SCORE_ROW_HEIGHT - 6
                )
                pygame.draw.rect(self.screen, ROW_ACTIVE_BG_COLOR, row_rect, border_radius=6)
            swatch = pygame.Rect(x, y + 2, 18, 18)
            pygame.draw.rect(self.screen, constants.PLAYER_COLORS[player.id], swatch)
            label = f"{player.name}: {player.total_area}"
            if player.consecutive_skips:
                label += f"  (skipped {player.consecutive_skips}/{game.skip_limit})"
            self._text(label, (x + 26, y), self.font, TEXT_COLOR if active else MUTED_TEXT_COLOR)
            y += layout.PANEL_SCORE_ROW_HEIGHT

        self._divider(layout.PANEL_DIVIDER_2_Y)

        y = layout.PANEL_STATUS_Y
        if game.state == TurnState.AWAITING_ROLL:
            self._text("Your turn - roll the dice!", (x, y), self.font, MUTED_TEXT_COLOR)
            self._button(layout.ROLL_BUTTON_RECT, "Roll Dice (D)")
        elif game.state == TurnState.CHOOSING_PLACEMENT:
            a, b = game.last_roll
            self._text(f"{a} x {b}", (x, y), self.font_dice)
            y += 36
            w, h = ui_state.current_dims
            self._text(f"Placing: {w} x {h}", (x, y))
            y += 26
            self._text("Click the board to place", (x, y), self.font_small, MUTED_TEXT_COLOR)
            self._button(layout.ROTATE_BUTTON_RECT, "Rotate (R)")
        elif game.state == TurnState.SKIPPED:
            self._text("No legal placement", (x, y), self.font, (170, 40, 40))
            y += 24
            self._text("for this roll - turn skipped.", (x, y), self.font_small, MUTED_TEXT_COLOR)
            self._button(layout.CONTINUE_BUTTON_RECT, "Continue (Space)")
        elif game.state == TurnState.GAME_OVER:
            self._text("Game over - see below", (x, y), self.font, MUTED_TEXT_COLOR)

        self._divider(layout.PANEL_HISTORY_DIVIDER_Y)
        self._text("History", (x, layout.PANEL_HISTORY_LABEL_Y), self.font_small, MUTED_TEXT_COLOR)
        self._draw_history(game)

        self._divider(layout.PANEL_FOOTER_DIVIDER_Y)
        self._button(layout.NEW_GAME_BUTTON_RECT, "New Game (N)")

    def _draw_history(self, game: Game) -> None:
        x = layout.PANEL_X
        y = layout.PANEL_HISTORY_START_Y
        entries = list(reversed(game.history))[: layout.PANEL_HISTORY_MAX_ROWS]
        if not entries:
            self._text("No moves yet", (x, y), self.font_small, MUTED_TEXT_COLOR)
            return
        for record in entries:
            player = game.players[record.player_id]
            swatch = pygame.Rect(x, y + 3, 10, 10)
            pygame.draw.rect(self.screen, constants.PLAYER_COLORS[record.player_id], swatch)
            if record.placed is not None:
                line = f"{player.name} placed {record.placed.width}x{record.placed.height}"
            else:
                a, b = record.roll
                line = f"{player.name} skipped (rolled {a},{b})"
            self._text(line, (x + 16, y), self.font_small, MUTED_TEXT_COLOR)
            y += layout.PANEL_HISTORY_ROW_HEIGHT

    def _draw_game_over(self, game: Game) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        p1, p2 = game.players[constants.PLAYER_1], game.players[constants.PLAYER_2]
        winner = game.winner()
        if winner is None:
            headline = "It's a tie!"
        else:
            headline = f"{game.players[winner].name} wins!"
        score_line = f"{p1.name}: {p1.total_area}    {p2.name}: {p2.total_area}"

        center_x = layout.WINDOW_WIDTH // 2
        center_y = layout.WINDOW_HEIGHT // 2

        if game.game_over_reason == GameOverReason.SKIP_LIMIT and game.skipped_out_player_id is not None:
            skipped_player = game.players[game.skipped_out_player_id]
            reason_line = f"{skipped_player.name} skipped {game.skip_limit} times in a row"
        elif game.game_over_reason == GameOverReason.PLAYER_BLOCKED and game.blocked_player_id is not None:
            blocked_player = game.players[game.blocked_player_id]
            reason_line = f"{blocked_player.name} is completely boxed in"
        else:
            reason_line = "Board is completely full"

        headline_surf = self.font_big.render(headline, True, (255, 255, 255))
        self.screen.blit(headline_surf, headline_surf.get_rect(center=(center_x, center_y - 24)))
        score_surf = self.font.render(score_line, True, (230, 230, 230))
        self.screen.blit(score_surf, score_surf.get_rect(center=(center_x, center_y + 14)))
        reason_surf = self.font_small.render(reason_line, True, (200, 200, 200))
        self.screen.blit(reason_surf, reason_surf.get_rect(center=(center_x, center_y + 44)))

        self._button(layout.GAME_OVER_NEW_GAME_BUTTON_RECT, "New Game (N)")
        self._button(layout.GAME_OVER_EXIT_BUTTON_RECT, "Exit (Esc)")
