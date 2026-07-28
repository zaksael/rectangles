from __future__ import annotations

import pygame

from .. import constants, persistence
from ..game import Game, GameOverReason, TurnState
from ..models import Rectangle
from ..series import RoundResult, Series
from . import layout
from .state import ConfirmAction, Screen, UIState

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
CARD_BG_COLOR = (255, 255, 255)
CARD_BORDER_COLOR = (215, 215, 222)
FLAG_COLOR = (230, 180, 30)
WALL_LINE_COLOR = (90, 88, 96)
LAST_MOVE_HIGHLIGHT_COLOR = (255, 225, 40)
STATUS_BANNER_BG_COLOR = (20, 20, 24, 215)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # The settings screen's content can be taller than the actual window
        # (see layout.SETTINGS_CONTENT_HEIGHT vs. the live window height); it's
        # drawn onto this full-height virtual surface and scrolled into view.
        self._settings_surface = pygame.Surface((layout.WINDOW_WIDTH, layout.SETTINGS_CONTENT_HEIGHT))
        self.font = pygame.font.SysFont("arial", 20)
        self.font_small = pygame.font.SysFont("arial", 15)
        self.font_big = pygame.font.SysFont("arial", 30, bold=True)
        self.font_dice = pygame.font.SysFont("arial", 28, bold=True)

    def resize(self, screen: pygame.Surface) -> None:
        self.screen = screen

    def draw(self, game: Game | None, ui_state: UIState, series: Series | None = None) -> None:
        self.screen.fill(BG_COLOR)
        if ui_state.screen == Screen.SETTINGS:
            window_width, window_height = self.screen.get_size()
            self._settings_surface.fill(BG_COLOR)
            real_screen, self.screen = self.screen, self._settings_surface
            self._draw_settings_screen(ui_state)
            self.screen = real_screen
            visible = pygame.Rect(0, ui_state.settings_scroll, window_width, window_height)
            self.screen.blit(self._settings_surface, (0, 0), area=visible)
            if ui_state.settings_scroll < layout.settings_max_scroll(window_height):
                # On a short window this strip can sit over genuine (clipped)
                # content rather than blank space below it - mask it first so
                # the hint always reads cleanly instead of overlapping.
                strip = pygame.Rect(0, window_height - 26, window_width, 26)
                self.screen.fill(BG_COLOR, strip)
                hint = self.font_small.render("scroll for more ▼", True, MUTED_TEXT_COLOR)
                self.screen.blit(hint, hint.get_rect(center=(window_width // 2, window_height - 14)))
        else:
            self._draw_board(game)
            if game.state == TurnState.CHOOSING_PLACEMENT:
                self._draw_coverable_cells(game, ui_state)
                if ui_state.hover_top_left is not None:
                    self._draw_ghost(ui_state)
            self._draw_status_banner(game)
            self._draw_panel(game, ui_state, series)
            if game.state == TurnState.GAME_OVER:
                self._draw_game_over(game, series)
            if ui_state.pending_confirmation is not None:
                self._draw_confirm_dialog(game, ui_state)
        pygame.display.flip()

    def _draw_settings_screen(self, ui_state: UIState) -> None:
        center_x = layout.WINDOW_WIDTH // 2
        mouse_pos = pygame.mouse.get_pos()

        def hovered(rect: pygame.Rect) -> bool:
            return rect.collidepoint(mouse_pos)

        title_surf = self.font_big.render("RECTANGLES", True, TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(center_x, 56)))
        subtitle_surf = self.font.render("Choose your settings", True, MUTED_TEXT_COLOR)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(center_x, 96)))

        for card_rect, header in (
            (layout.SETTINGS_BOARD_CARD_RECT, "Board Setup"),
            (layout.SETTINGS_MATCH_CARD_RECT, "Opponent & Match"),
            (layout.SETTINGS_HOUSE_RULES_CARD_RECT, "House Rules"),
        ):
            pygame.draw.rect(self.screen, CARD_BG_COLOR, card_rect, border_radius=12)
            pygame.draw.rect(self.screen, CARD_BORDER_COLOR, card_rect, width=1, border_radius=12)
            header_surf = self.font.render(header, True, TEXT_COLOR)
            self.screen.blit(header_surf, header_surf.get_rect(center=(card_rect.centerx, card_rect.top + 26)))

        board_label = self.font.render("Board size", True, TEXT_COLOR)
        self.screen.blit(board_label, board_label.get_rect(center=(layout.SETTINGS_LEFT_COLUMN_X, 180)))
        for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
            self._button(
                rect, f"{value}x{value}", selected=value == ui_state.selected_board_size, hovered=hovered(rect)
            )

        skip_label = self.font.render("Skip limit", True, TEXT_COLOR)
        self.screen.blit(skip_label, skip_label.get_rect(center=(layout.SETTINGS_LEFT_COLUMN_X, 280)))
        for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
            self._button(rect, str(value), selected=value == ui_state.selected_skip_limit, hovered=hovered(rect))

        toggle_label_y = layout.SETTINGS_HOUSE_RULES_CARD_RECT.top + 70
        for label_text, column_x, rect, enabled_flag in (
            ("Doubles bonus turn", layout.SETTINGS_RULE_COLUMN_1_X,
             layout.SETTINGS_DOUBLES_BUTTON_RECT, ui_state.selected_doubles_enabled),
            ("Flag Conquest", layout.SETTINGS_RULE_COLUMN_2_X,
             layout.SETTINGS_FLAG_CONQUEST_BUTTON_RECT, ui_state.selected_flag_conquest_enabled),
            ("Walls", layout.SETTINGS_RULE_COLUMN_3_X,
             layout.SETTINGS_WALLS_BUTTON_RECT, ui_state.selected_walls_enabled),
        ):
            label_surf = self.font.render(label_text, True, TEXT_COLOR)
            self.screen.blit(label_surf, label_surf.get_rect(center=(column_x, toggle_label_y)))
            self._button(
                rect, "ON" if enabled_flag else "OFF", selected=enabled_flag, hovered=hovered(rect)
            )

        flag_bonus_label = self.font.render(
            "Flag bonus points",
            True,
            TEXT_COLOR if ui_state.selected_flag_conquest_enabled else MUTED_TEXT_COLOR,
        )
        self.screen.blit(
            flag_bonus_label,
            flag_bonus_label.get_rect(
                center=(layout.SETTINGS_RULE_COLUMN_2_X, layout.SETTINGS_HOUSE_RULES_CARD_RECT.top + 170)
            ),
        )
        for value, rect in layout.SETTINGS_FLAG_BONUS_BUTTON_RECTS.items():
            self._button(
                rect,
                f"+{value}",
                enabled=ui_state.selected_flag_conquest_enabled,
                selected=value == ui_state.selected_flag_bonus_points,
                hovered=ui_state.selected_flag_conquest_enabled and hovered(rect),
            )

        bot_label = self.font.render("vs Bot (P2)", True, TEXT_COLOR)
        self.screen.blit(bot_label, bot_label.get_rect(center=(layout.SETTINGS_RIGHT_COLUMN_X, 180)))
        self._button(
            layout.SETTINGS_BOT_BUTTON_RECT,
            "ON" if ui_state.selected_bot_enabled else "OFF",
            selected=ui_state.selected_bot_enabled,
            hovered=hovered(layout.SETTINGS_BOT_BUTTON_RECT),
        )

        series_label = self.font.render("Series length (for Start Series)", True, TEXT_COLOR)
        self.screen.blit(series_label, series_label.get_rect(center=(layout.SETTINGS_RIGHT_COLUMN_X, 280)))
        for value, rect in layout.SETTINGS_SERIES_LENGTH_BUTTON_RECTS.items():
            self._button(
                rect, f"{value} Rounds", selected=value == ui_state.selected_series_length, hovered=hovered(rect)
            )

        difficulty_label = self.font.render(
            "Bot difficulty",
            True,
            TEXT_COLOR if ui_state.selected_bot_enabled else MUTED_TEXT_COLOR,
        )
        self.screen.blit(
            difficulty_label, difficulty_label.get_rect(center=(layout.SETTINGS_RIGHT_COLUMN_X, 375))
        )
        for value, rect in layout.SETTINGS_BOT_DIFFICULTY_BUTTON_RECTS.items():
            self._button(
                rect,
                value,
                enabled=ui_state.selected_bot_enabled,
                selected=value == ui_state.selected_bot_difficulty,
                hovered=ui_state.selected_bot_enabled and hovered(rect),
            )

        self._button(
            layout.SETTINGS_START_BUTTON_RECT,
            "Start Game (Space)",
            hovered=hovered(layout.SETTINGS_START_BUTTON_RECT),
        )
        self._button(
            layout.SETTINGS_START_SERIES_BUTTON_RECT,
            "Start Series",
            hovered=hovered(layout.SETTINGS_START_SERIES_BUTTON_RECT),
        )
        self._button(
            layout.SETTINGS_EXIT_BUTTON_RECT, "Exit (Esc)", hovered=hovered(layout.SETTINGS_EXIT_BUTTON_RECT)
        )
        if persistence.has_save():
            self._button(
                layout.SETTINGS_RESUME_BUTTON_RECT,
                "Resume Game (R)",
                hovered=hovered(layout.SETTINGS_RESUME_BUTTON_RECT),
            )

    def _draw_board(self, game: Game) -> None:
        for r in range(game.board.size):
            for c in range(game.board.size):
                rect = layout.cell_rect(r, c)
                pygame.draw.rect(self.screen, EMPTY_CELL_COLOR, rect)
                pygame.draw.rect(self.screen, GRID_LINE_COLOR, rect, width=1)

        self._draw_flags(game)

        for player in game.players.values():
            color = constants.PLAYER_COLORS[player.id]
            border = constants.PLAYER_BORDER_COLORS[player.id]
            for piece in player.pieces:
                rect = layout.piece_rect(piece.top_left, piece.width, piece.height)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, border, rect, width=3)

        self._draw_last_move_highlight(game)
        self._draw_walls(game)

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

    def _last_placed_rect(self, game: Game) -> Rectangle | None:
        return next((record.placed for record in reversed(game.history) if record.placed is not None), None)

    def _draw_last_move_highlight(self, game: Game) -> None:
        last_placed = self._last_placed_rect(game)
        if last_placed is None:
            return
        rect = layout.piece_rect(last_placed.top_left, last_placed.width, last_placed.height).inflate(4, 4)
        pygame.draw.rect(self.screen, LAST_MOVE_HIGHLIGHT_COLOR, rect, width=3)

    def _is_doubles_bonus_turn(self, game: Game) -> bool:
        return (
            game.doubles_enabled
            and bool(game.history)
            and game.history[-1].player_id == game.current_player_id
            and game.history[-1].roll[0] == game.history[-1].roll[1]
        )

    def _status_banner_message(self, game: Game) -> str | None:
        if game.state == TurnState.SKIPPED:
            return f"{game.current_player.name} skipped - no legal placement!"
        if game.state == TurnState.AWAITING_ROLL and self._is_doubles_bonus_turn(game):
            return f"Doubles! {game.current_player.name} rolls again"
        return None

    def _draw_status_banner(self, game: Game) -> None:
        message = self._status_banner_message(game)
        if message is None:
            return
        text_surf = self.font.render(message, True, (255, 255, 255))
        banner_rect = text_surf.get_rect().inflate(48, 28)
        # Centered on the full board column (not just the current board_size's
        # smaller rect), so it stays on-screen even for the smallest boards.
        banner_rect.centerx = layout.BOARD_PX // 2
        banner_rect.top = 16
        overlay = pygame.Surface(banner_rect.size, pygame.SRCALPHA)
        overlay.fill(STATUS_BANNER_BG_COLOR)
        self.screen.blit(overlay, banner_rect.topleft)
        pygame.draw.rect(self.screen, LAST_MOVE_HIGHLIGHT_COLOR, banner_rect, width=2, border_radius=8)
        self.screen.blit(text_surf, text_surf.get_rect(center=banner_rect.center))

    def _draw_walls(self, game: Game) -> None:
        for edge in game.board.wall_edges:
            a, b = tuple(edge)
            (r1, c1), (r2, c2) = (a, b) if a <= b else (b, a)
            if r1 == r2:
                # Horizontally adjacent cells (c1 < c2): vertical boundary line between them.
                x = layout.cell_rect(r1, c2).left
                top = layout.cell_rect(r1, c1).top
                pygame.draw.line(self.screen, WALL_LINE_COLOR, (x, top), (x, top + layout.CELL_PX), width=4)
            else:
                # Vertically adjacent cells (r1 < r2): horizontal boundary line between them.
                y = layout.cell_rect(r2, c1).top
                left = layout.cell_rect(r1, c1).left
                pygame.draw.line(self.screen, WALL_LINE_COLOR, (left, y), (left + layout.CELL_PX, y), width=4)

    def _draw_flags(self, game: Game) -> None:
        for r, c in game.board.flag_cells:
            if game.board.owner_at(r, c) is not None:
                continue
            cx, cy = layout.cell_rect(r, c).center
            half = layout.CELL_PX // 4
            points = [(cx - half, cy - half), (cx - half, cy + half), (cx + half, cy)]
            pygame.draw.polygon(self.screen, FLAG_COLOR, points)

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

    def _button(
        self,
        rect: pygame.Rect,
        label: str,
        enabled: bool = True,
        selected: bool = False,
        hovered: bool = False,
    ) -> None:
        if not enabled:
            color = BUTTON_DISABLED_COLOR
        elif selected:
            color = BUTTON_SELECTED_COLOR
        elif hovered:
            color = BUTTON_HOVER_COLOR
        else:
            color = BUTTON_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        if selected and enabled:
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

    def _draw_panel(self, game: Game, ui_state: UIState, series: Series | None = None) -> None:
        window_height = self.screen.get_height()
        pygame.draw.rect(self.screen, PANEL_BG_COLOR, layout.panel_rect(window_height))
        x = layout.PANEL_X

        self._text("RECTANGLES", (x, layout.PANEL_HEADER_Y), self.font_big)
        if series is not None:
            p1, p2 = game.players[constants.PLAYER_1], game.players[constants.PLAYER_2]
            series_line = (
                f"{series.length} Rounds · Game {series.games_played + 1} · "
                f"{p1.name} {series.scores[constants.PLAYER_1]}-{series.scores[constants.PLAYER_2]} {p2.name}"
            )
            self._text(series_line, (x, layout.PANEL_HEADER_Y + 34), self.font_small, MUTED_TEXT_COLOR)
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
            label = f"{player.name}: {game.total_score(player)}"
            if player.flags_captured:
                label += f"  F{player.flags_captured}"
            if player.consecutive_skips:
                label += f"  (skipped {player.consecutive_skips}/{game.skip_limit})"
            self._text(label, (x + 26, y), self.font, TEXT_COLOR if active else MUTED_TEXT_COLOR)
            y += layout.PANEL_SCORE_ROW_HEIGHT

        self._divider(layout.PANEL_DIVIDER_2_Y)

        y = layout.PANEL_STATUS_Y
        if game.state == TurnState.AWAITING_ROLL:
            prompt = "Your turn - roll the dice!"
            if self._is_doubles_bonus_turn(game):
                prompt = "Doubles! Roll again"
            self._text(prompt, (x, y), self.font, MUTED_TEXT_COLOR)
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
            a, b = game.last_roll
            self._text(f"{a} x {b}", (x, y), self.font_dice)
            y += 36
            self._text("No legal placement", (x, y), self.font, (170, 40, 40))
            y += 24
            self._text("for this roll - turn skipped.", (x, y), self.font_small, MUTED_TEXT_COLOR)
            self._button(layout.CONTINUE_BUTTON_RECT, "Continue (Space)")
        elif game.state == TurnState.GAME_OVER:
            self._text("Game over - see below", (x, y), self.font, MUTED_TEXT_COLOR)

        self._divider(layout.PANEL_HISTORY_DIVIDER_Y)
        history_label = "History (scrolled)" if ui_state.history_scroll > 0 else "History"
        self._text(history_label, (x, layout.PANEL_HISTORY_LABEL_Y), self.font_small, MUTED_TEXT_COLOR)
        self._draw_history(game, ui_state)

        if series is not None:
            self._draw_series_stats(series)

        self._divider(layout.panel_footer_divider_y(window_height))
        self._button(layout.surrender_button_rect(window_height), "Surrender (S)")
        self._button(layout.new_game_button_rect(window_height), "New Game (N)")
        self._button(layout.exit_button_rect(window_height), "Exit (Esc)")

    def _draw_history(self, game: Game, ui_state: UIState) -> None:
        x = layout.PANEL_X
        y = layout.PANEL_HISTORY_START_Y
        remaining = list(reversed(game.history))[ui_state.history_scroll :]
        has_more = len(remaining) > layout.PANEL_HISTORY_MAX_ROWS
        visible_rows = layout.PANEL_HISTORY_MAX_ROWS - 1 if has_more else layout.PANEL_HISTORY_MAX_ROWS
        entries = remaining[:visible_rows]

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
            if game.doubles_enabled and record.roll[0] == record.roll[1]:
                line += " - doubles!"
            self._text(line, (x + 16, y), self.font_small, MUTED_TEXT_COLOR)
            y += layout.PANEL_HISTORY_ROW_HEIGHT

        if has_more:
            self._text("scroll for more ▼", (x, y), self.font_small, MUTED_TEXT_COLOR)

    def _round_row(self, series: Series, index: int, result: RoundResult) -> list[str]:
        row = [str(index), str(result.total[constants.PLAYER_1])]
        if series.flag_conquest_enabled:
            row.append(str(result.flags_captured[constants.PLAYER_1]))
        row.append(str(result.total[constants.PLAYER_2]))
        if series.flag_conquest_enabled:
            row.append(str(result.flags_captured[constants.PLAYER_2]))
        return row

    def _series_totals_row(self, series: Series) -> list[str]:
        row = ["Total", str(series.scores[constants.PLAYER_1])]
        if series.flag_conquest_enabled:
            row.append(str(series.total_flags_captured(constants.PLAYER_1)))
        row.append(str(series.scores[constants.PLAYER_2]))
        if series.flag_conquest_enabled:
            row.append(str(series.total_flags_captured(constants.PLAYER_2)))
        return row

    def _series_table_rows(self, series: Series) -> list[list[str]]:
        rows = [self._round_row(series, index, result) for index, result in enumerate(series.rounds, start=1)]
        if series.rounds:
            rows.append(self._series_totals_row(series))
        return rows

    def _series_table_columns(self, series: Series, *, panel: bool) -> list[tuple[str, int]]:
        if series.flag_conquest_enabled:
            if panel:
                return [("Rnd", 32), ("P1", 88), ("F", 34), ("P2", 88), ("F", 34)]
            # Centered on the whole window (board + panel) like the rest of the overlay's
            # text, so this must stay narrow enough that it doesn't creep past the board's
            # right edge into the panel's own (separately drawn) series table.
            return [("Rnd", 60), ("P1", 130), ("F", 65), ("P2", 130), ("F", 65)]
        if panel:
            return [("Rnd", 40), ("P1", 126), ("P2", 126)]
        return [("Rnd", 70), ("P1", 220), ("P2", 220)]

    def _draw_table(
        self,
        x: int,
        y: int,
        columns: list[tuple[str, int]],
        rows: list[list[str]],
        row_height: int,
        font: pygame.font.Font,
        header_color: tuple,
        row_color: tuple,
    ) -> None:
        def draw_row(values: list[str], row_y: int, color: tuple) -> None:
            cx = x
            for i, (value, (_, width)) in enumerate(zip(values, columns)):
                surf = font.render(value, True, color)
                rect = surf.get_rect()
                if i == 0:
                    rect.topleft = (cx, row_y)
                else:
                    rect.topright = (cx + width, row_y)
                self.screen.blit(surf, rect)
                cx += width

        draw_row([header for header, _ in columns], y, header_color)
        y += row_height
        table_width = sum(width for _, width in columns)
        pygame.draw.line(self.screen, DIVIDER_COLOR, (x, y - 4), (x + table_width, y - 4))
        for row in rows:
            draw_row(row, y, row_color)
            y += row_height

    def _panel_series_rows(self, series: Series) -> tuple[list[list[str]], int]:
        # Caps the panel's (compact, always-visible) table at PANEL_SERIES_MAX_ROWS
        # lines regardless of series length, keeping the totals row and the most
        # recent rounds, with older rounds folded behind a "+N earlier" note - the
        # full round-by-round table is always available on the game-over overlay,
        # which isn't bound by this same fixed-pixel panel budget.
        rows = self._series_table_rows(series)
        max_data_rows = layout.PANEL_SERIES_MAX_ROWS - 1  # minus the header line
        if len(rows) <= max_data_rows:
            return rows, 0
        round_rows, totals_row = rows[:-1], rows[-1]
        keep = max_data_rows - 2  # totals row + the "N earlier" note both reserved
        visible_rounds = round_rows[-keep:] if keep > 0 else []
        hidden = len(round_rows) - len(visible_rounds)
        return visible_rounds + [totals_row], hidden

    def _draw_series_stats(self, series: Series) -> None:
        x = layout.PANEL_X
        self._divider(layout.PANEL_SERIES_DIVIDER_Y)
        self._text("Series Stats", (x, layout.PANEL_SERIES_LABEL_Y), self.font_small, MUTED_TEXT_COLOR)
        rows, hidden = self._panel_series_rows(series)
        self._draw_table(
            x,
            layout.PANEL_SERIES_START_Y,
            self._series_table_columns(series, panel=True),
            rows,
            layout.PANEL_SERIES_ROW_HEIGHT,
            self.font_small,
            MUTED_TEXT_COLOR,
            MUTED_TEXT_COLOR,
        )
        if hidden:
            note_y = layout.PANEL_SERIES_START_Y + (len(rows) + 1) * layout.PANEL_SERIES_ROW_HEIGHT
            note = f"+{hidden} earlier round{'s' if hidden != 1 else ''}"
            self._text(note, (x, note_y), self.font_small, MUTED_TEXT_COLOR)

    def _draw_game_over(self, game: Game, series: Series | None = None) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        p1, p2 = game.players[constants.PLAYER_1], game.players[constants.PLAYER_2]
        winner = game.winner()

        series_complete = series is not None and series.is_complete()
        if series_complete:
            series_winner = series.winner()
            headline = (
                "Series tied!" if series_winner is None else f"{game.players[series_winner].name} wins the series!"
            )
        elif winner is None:
            headline = "It's a tie!"
        else:
            headline = f"{game.players[winner].name} wins!"
        score_line = f"{p1.name}: {game.total_score(p1)}    {p2.name}: {game.total_score(p2)}"

        window_width, window_height = self.screen.get_size()
        center_x = window_width // 2
        center_y = window_height // 2

        if game.game_over_reason == GameOverReason.SKIP_LIMIT and game.skipped_out_player_id is not None:
            skipped_player = game.players[game.skipped_out_player_id]
            reason_line = f"{skipped_player.name} skipped {game.skip_limit} times in a row"
        elif game.game_over_reason == GameOverReason.PLAYER_BLOCKED and game.blocked_player_id is not None:
            blocked_player = game.players[game.blocked_player_id]
            reason_line = f"{blocked_player.name} is completely boxed in"
        elif game.game_over_reason == GameOverReason.SURRENDER and game.surrendered_player_id is not None:
            surrendered_player = game.players[game.surrendered_player_id]
            reason_line = f"{surrendered_player.name} surrendered"
        else:
            reason_line = "Board is completely full"

        headline_surf = self.font_big.render(headline, True, (255, 255, 255))
        self.screen.blit(headline_surf, headline_surf.get_rect(center=(center_x, center_y - 24)))
        score_surf = self.font.render(score_line, True, (230, 230, 230))
        self.screen.blit(score_surf, score_surf.get_rect(center=(center_x, center_y + 14)))

        if series is not None:
            series_line = (
                f"Series: {p1.name} {series.scores[constants.PLAYER_1]} - "
                f"{series.scores[constants.PLAYER_2]} {p2.name}  ({series.length} Rounds)"
            )
            series_surf = self.font_small.render(series_line, True, (200, 200, 200))
            self.screen.blit(series_surf, series_surf.get_rect(center=(center_x, center_y + 44)))
            reason_y = center_y + 68
        else:
            reason_y = center_y + 44
        reason_surf = self.font_small.render(reason_line, True, (200, 200, 200))
        self.screen.blit(reason_surf, reason_surf.get_rect(center=(center_x, reason_y)))

        new_game_label = "New Game (N)" if series is None or series_complete else "Next Game (N)"
        new_game_rect = layout.game_over_new_game_button_rect(window_width, window_height)
        self._button(new_game_rect, new_game_label)
        self._button(layout.game_over_exit_button_rect(window_width, window_height), "Exit (Esc)")

        if series is not None and series.rounds:
            columns = self._series_table_columns(series, panel=False)
            table_width = sum(width for _, width in columns)
            self._draw_table(
                center_x - table_width // 2,
                new_game_rect.bottom + 40,
                columns,
                self._series_table_rows(series),
                layout.PANEL_SERIES_ROW_HEIGHT,
                self.font_small,
                (200, 200, 200),
                (200, 200, 200),
            )

    def _draw_confirm_dialog(self, game: Game, ui_state: UIState) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        window_width, window_height = self.screen.get_size()
        dialog_rect = layout.confirm_dialog_rect(window_width, window_height)
        pygame.draw.rect(self.screen, PANEL_BG_COLOR, dialog_rect, border_radius=8)

        if ui_state.pending_confirmation == ConfirmAction.SURRENDER:
            opponent_id = (
                constants.PLAYER_2 if game.current_player_id == constants.PLAYER_1 else constants.PLAYER_1
            )
            message = f"Surrender? {game.players[opponent_id].name} will win."
        else:
            messages = {
                ConfirmAction.NEW_GAME: "Abandon this match and return to settings?",
                ConfirmAction.EXIT: "Quit? Your progress will be saved.",
            }
            message = messages[ui_state.pending_confirmation]
        message_surf = self.font.render(message, True, TEXT_COLOR)
        message_rect = message_surf.get_rect(center=(dialog_rect.centerx, dialog_rect.top + 56))
        self.screen.blit(message_surf, message_rect)

        self._button(layout.confirm_yes_button_rect(window_width, window_height), "Yes (Enter)")
        self._button(layout.confirm_no_button_rect(window_width, window_height), "No (Esc)")
