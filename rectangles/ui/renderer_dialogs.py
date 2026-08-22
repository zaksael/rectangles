from __future__ import annotations

import pygame

from .. import constants
from ..game import Game, GameOverReason
from ..series import Series
from ..tournament import Bracket
from . import layout
from .colors import OVERLAY_COLOR, TEXT_COLOR
from .state import ConfirmAction, UIState


class DialogsMixin:
    def _draw_game_over(self, game: Game, series: Series | None = None, tournament: Bracket | None = None) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill(OVERLAY_COLOR)
        self.screen.blit(overlay, (0, 0))

        p1, p2 = game.players[constants.PLAYER_1], game.players[constants.PLAYER_2]
        winner = game.winner()

        match = tournament.current_match() if tournament is not None else None
        is_tiebreak = match is not None and game is match.tiebreak_game

        series_complete = series is not None and series.is_complete() and not is_tiebreak
        if is_tiebreak:
            headline = (
                f"{game.players[winner].name} wins the tiebreak!"
                if winner is not None
                else "Tiebreak tied - resolving by chance..."
            )
        elif series_complete:
            series_winner = series.winner()
            headline = (
                "Series tied!" if series_winner is None else f"{game.players[series_winner].name} wins the series!"
            )
        elif winner is None:
            headline = "It's a tie!"
        else:
            headline = f"{game.players[winner].name} wins!"
        score_line = f"{p1.name}: {game.total_score(p1)}    {p2.name}: {game.total_score(p2)}"

        center_x = layout.DESIGN_WIDTH // 2
        center_y = layout.DESIGN_HEIGHT // 2

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

        if is_tiebreak:
            new_game_label = "Next Match (N)"
        elif tournament is not None:
            if series is not None and not series.is_complete():
                new_game_label = "Next Game (N)"
            elif series is not None and series.winner() is None:
                new_game_label = "Tiebreak (N)"
            else:
                new_game_label = "Next Match (N)"
        else:
            new_game_label = "New Game (N)" if series is None or series_complete else "Next Game (N)"
        new_game_rect = layout.GAME_OVER_NEW_GAME_BUTTON_RECT
        self._button(new_game_rect, new_game_label)
        self._button(layout.GAME_OVER_REPLAY_BUTTON_RECT, "Replay")
        self._button(layout.GAME_OVER_EXIT_BUTTON_RECT, "Exit (Esc)")
        if tournament is not None:
            self._button(layout.GAME_OVER_BRACKET_BUTTON_RECT, "Bracket")

        if series is not None and series.rounds:
            # Pushed down an extra row when the Bracket button is also drawn
            # below the New Game/Replay/Exit row, so the two never overlap.
            table_top = new_game_rect.bottom + 40
            if tournament is not None:
                table_top = layout.GAME_OVER_BRACKET_BUTTON_RECT.bottom + 24
            columns = self._series_table_columns(series, panel=False)
            table_width = sum(width for _, width in columns)
            self._draw_table(
                center_x - table_width // 2,
                table_top,
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

        dialog_rect = layout.CONFIRM_DIALOG_RECT
        self._draw_card(dialog_rect)

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

        self._button(layout.CONFIRM_YES_BUTTON_RECT, "Yes (Enter)")
        self._button(layout.CONFIRM_NO_BUTTON_RECT, "No (Esc)", outline=True)
