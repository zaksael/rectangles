from __future__ import annotations

import pygame

from .. import constants, persistence
from ..game import Game, GameOverReason, TurnState
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


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 20)
        self.font_small = pygame.font.SysFont("arial", 15)
        self.font_big = pygame.font.SysFont("arial", 30, bold=True)
        self.font_dice = pygame.font.SysFont("arial", 28, bold=True)

    def draw(self, game: Game | None, ui_state: UIState, series: Series | None = None) -> None:
        self.screen.fill(BG_COLOR)
        if ui_state.screen == Screen.SETTINGS:
            self._draw_settings_screen(ui_state)
        else:
            self._draw_board(game)
            if game.state == TurnState.CHOOSING_PLACEMENT:
                self._draw_coverable_cells(game, ui_state)
                if ui_state.hover_top_left is not None:
                    self._draw_ghost(ui_state)
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
            (layout.SETTINGS_LEFT_CARD_RECT, "Game Rules"),
            (layout.SETTINGS_RIGHT_CARD_RECT, "Opponent & Match"),
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

        doubles_label = self.font.render("Doubles bonus turn", True, TEXT_COLOR)
        self.screen.blit(
            doubles_label, doubles_label.get_rect(center=(layout.SETTINGS_LEFT_COLUMN_X, 380))
        )
        self._button(
            layout.SETTINGS_DOUBLES_BUTTON_RECT,
            "ON" if ui_state.selected_doubles_enabled else "OFF",
            selected=ui_state.selected_doubles_enabled,
            hovered=hovered(layout.SETTINGS_DOUBLES_BUTTON_RECT),
        )

        flag_label = self.font.render("Flag Conquest", True, TEXT_COLOR)
        self.screen.blit(
            flag_label, flag_label.get_rect(center=(layout.SETTINGS_LEFT_COLUMN_X, 480))
        )
        self._button(
            layout.SETTINGS_FLAG_CONQUEST_BUTTON_RECT,
            "ON" if ui_state.selected_flag_conquest_enabled else "OFF",
            selected=ui_state.selected_flag_conquest_enabled,
            hovered=hovered(layout.SETTINGS_FLAG_CONQUEST_BUTTON_RECT),
        )

        flag_bonus_label = self.font.render(
            "Flag bonus points",
            True,
            TEXT_COLOR if ui_state.selected_flag_conquest_enabled else MUTED_TEXT_COLOR,
        )
        self.screen.blit(
            flag_bonus_label, flag_bonus_label.get_rect(center=(layout.SETTINGS_LEFT_COLUMN_X, 580))
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

        for i, line in enumerate(("The bot plays Player 2 automatically", "when turned on, in every mode.")):
            hint_surf = self.font_small.render(line, True, MUTED_TEXT_COLOR)
            self.screen.blit(hint_surf, hint_surf.get_rect(center=(layout.SETTINGS_RIGHT_COLUMN_X, 400 + i * 20)))

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

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

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
        pygame.draw.rect(self.screen, PANEL_BG_COLOR, layout.PANEL_RECT)
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
                label += f"  🚩{player.flags_captured}"
            if player.consecutive_skips:
                label += f"  (skipped {player.consecutive_skips}/{game.skip_limit})"
            self._text(label, (x + 26, y), self.font, TEXT_COLOR if active else MUTED_TEXT_COLOR)
            y += layout.PANEL_SCORE_ROW_HEIGHT

        self._divider(layout.PANEL_DIVIDER_2_Y)

        y = layout.PANEL_STATUS_Y
        if game.state == TurnState.AWAITING_ROLL:
            prompt = "Your turn - roll the dice!"
            if (
                game.doubles_enabled
                and game.history
                and game.history[-1].player_id == game.current_player_id
                and game.history[-1].roll[0] == game.history[-1].roll[1]
            ):
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

        self._divider(layout.PANEL_FOOTER_DIVIDER_Y)
        self._button(layout.SURRENDER_BUTTON_RECT, "Surrender (S)")
        self._button(layout.NEW_GAME_BUTTON_RECT, "New Game (N)")
        self._button(layout.EXIT_BUTTON_RECT, "Exit (Esc)")

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

    def _format_round_line(self, series: Series, index: int, result: RoundResult) -> str:
        p1_flags = ""
        p2_flags = ""
        if series.flag_conquest_enabled:
            if result.flags_captured[constants.PLAYER_1]:
                p1_flags = f" (🚩{result.flags_captured[constants.PLAYER_1]})"
            if result.flags_captured[constants.PLAYER_2]:
                p2_flags = f" (🚩{result.flags_captured[constants.PLAYER_2]})"
        return (
            f"R{index}: P1 {result.total[constants.PLAYER_1]}{p1_flags}  -  "
            f"{result.total[constants.PLAYER_2]}{p2_flags} P2"
        )

    def _format_series_totals_line(self, series: Series) -> str:
        p1_flags = f" (🚩{series.total_flags_captured(constants.PLAYER_1)})" if series.flag_conquest_enabled else ""
        p2_flags = f" (🚩{series.total_flags_captured(constants.PLAYER_2)})" if series.flag_conquest_enabled else ""
        return (
            f"Totals: P1 {series.scores[constants.PLAYER_1]}{p1_flags}  -  "
            f"{series.scores[constants.PLAYER_2]}{p2_flags} P2"
        )

    def _draw_series_stats(self, series: Series) -> None:
        x = layout.PANEL_X
        self._divider(layout.PANEL_SERIES_DIVIDER_Y)
        self._text("Series Stats", (x, layout.PANEL_SERIES_LABEL_Y), self.font_small, MUTED_TEXT_COLOR)
        y = layout.PANEL_SERIES_START_Y
        for index, result in enumerate(series.rounds, start=1):
            self._text(self._format_round_line(series, index, result), (x, y), self.font_small, MUTED_TEXT_COLOR)
            y += layout.PANEL_SERIES_ROW_HEIGHT
        if series.rounds:
            self._text(self._format_series_totals_line(series), (x, y), self.font_small, MUTED_TEXT_COLOR)

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

        center_x = layout.WINDOW_WIDTH // 2
        center_y = layout.WINDOW_HEIGHT // 2

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
        self._button(layout.GAME_OVER_NEW_GAME_BUTTON_RECT, new_game_label)
        self._button(layout.GAME_OVER_EXIT_BUTTON_RECT, "Exit (Esc)")

        if series is not None and series.rounds:
            y = layout.GAME_OVER_NEW_GAME_BUTTON_RECT.bottom + 40
            for index, result in enumerate(series.rounds, start=1):
                line_surf = self.font_small.render(
                    self._format_round_line(series, index, result), True, (200, 200, 200)
                )
                self.screen.blit(line_surf, line_surf.get_rect(center=(center_x, y)))
                y += layout.PANEL_SERIES_ROW_HEIGHT
            totals_surf = self.font_small.render(self._format_series_totals_line(series), True, (200, 200, 200))
            self.screen.blit(totals_surf, totals_surf.get_rect(center=(center_x, y)))

    def _draw_confirm_dialog(self, game: Game, ui_state: UIState) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        pygame.draw.rect(self.screen, PANEL_BG_COLOR, layout.CONFIRM_DIALOG_RECT, border_radius=8)

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
        message_rect = message_surf.get_rect(
            center=(layout.CONFIRM_DIALOG_RECT.centerx, layout.CONFIRM_DIALOG_RECT.top + 56)
        )
        self.screen.blit(message_surf, message_rect)

        self._button(layout.CONFIRM_YES_BUTTON_RECT, "Yes (Enter)")
        self._button(layout.CONFIRM_NO_BUTTON_RECT, "No (Esc)")
