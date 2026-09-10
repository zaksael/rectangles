from __future__ import annotations

import pygame

from .. import constants
from ..constants import CellKind
from ..game import Game, TurnState
from ..models import TurnRecord
from ..series import RoundResult, Series
from ..tournament import Bracket
from . import layout
from .colors import DIVIDER_COLOR, MUTED_TEXT_COLOR, PANEL_BG_COLOR, ROW_ACTIVE_BG_COLOR, TEXT_COLOR
from .state import UIState


class PanelMixin:
    def _reroll_label(self, game: Game, short: bool = False) -> str:
        limit = game.effective_reroll_limit(game.current_player)
        remaining = limit - game.current_player.rerolls_used
        if short:
            return f"R{remaining}"
        return f"Reroll ({remaining}/{limit})"

    def _wrap_suffixes(self, suffixes: list[str], font: pygame.font.Font, max_width: int) -> list[str]:
        # Packs whole suffix items onto a line, never splitting one mid-item
        # (unlike _wrap_text's word-wrap, which would break "Prize 1" apart) -
        # up to 6 items can appear at once with every house rule on, which no
        # longer reliably fits one line (see PANEL_SCORE_ROW_HEIGHT above).
        lines = [suffixes[0]]
        for item in suffixes[1:]:
            candidate = "  ".join((lines[-1], item))
            if font.size(candidate)[0] <= max_width:
                lines[-1] = candidate
            else:
                lines.append(item)
        return lines

    def _draw_score_row(
        self, x: int, y: int, player_id: int, primary: str, suffixes: list[str], color: tuple[int, int, int]
    ) -> None:
        swatch = pygame.Rect(x, y + 2, 18, 18)
        pygame.draw.rect(self.screen, constants.PLAYER_COLORS[player_id], swatch)
        self._text(primary, (x + 26, y), self.font, color)
        if suffixes:
            line_y = y + layout.PANEL_SCORE_LINE2_DY
            for line in self._wrap_suffixes(suffixes, self.font_small, layout.PANEL_CONTENT_WIDTH):
                self._text(line, (x + 26, line_y), self.font_small, MUTED_TEXT_COLOR)
                line_y += self.font_small.get_linesize()

    def _tournament_match_number(self, tournament: Bracket) -> tuple[int, int]:
        played = sum(len(round_) for round_ in tournament.rounds[:-1]) + tournament.current_match_index + 1
        total = len(tournament.participants) - 1
        return played, total

    def _draw_panel(
        self, game: Game, ui_state: UIState, series: Series | None = None, tournament: Bracket | None = None
    ) -> None:
        pygame.draw.rect(self.screen, PANEL_BG_COLOR, layout.PANEL_RECT)
        x = layout.PANEL_X

        self._text("RECTANGLES", (x, layout.PANEL_HEADER_Y), self.font_big)
        match = tournament.current_match() if tournament is not None else None
        is_tiebreak = match is not None and game is match.tiebreak_game
        if is_tiebreak:
            p1, p2 = game.players[constants.PLAYER_1], game.players[constants.PLAYER_2]
            played, total = self._tournament_match_number(tournament)
            self._text(
                f"Match {played}/{total} · Tiebreak · {p1.name} vs {p2.name}",
                (x, layout.PANEL_HEADER_Y + 34),
                self.font_small,
                MUTED_TEXT_COLOR,
            )
        elif series is not None:
            p1, p2 = game.players[constants.PLAYER_1], game.players[constants.PLAYER_2]
            prefix = ""
            if tournament is not None:
                played, total = self._tournament_match_number(tournament)
                prefix = f"Match {played}/{total} · "
            series_line = (
                f"{prefix}{series.length} Rounds · Game {series.games_played + 1} · "
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
            primary = f"{player.name}: {game.total_score(player)}"

            suffixes = []
            prize = player.special_captures.get(CellKind.PRIZE, 0)
            if prize:
                suffixes.append(f"Prize {prize}")
            pitfall = player.special_captures.get(CellKind.PITFALL, 0)
            if pitfall:
                suffixes.append(f"Pitfall {pitfall}")
            steal_swing = (
                player.special_captures.get(CellKind.STEAL, 0)
                - game._other_player(player).special_captures.get(CellKind.STEAL, 0)
            ) * game.points_for(CellKind.STEAL)
            if steal_swing:
                suffixes.append(f"Steal {steal_swing:+d}")
            if game.self_enclosed_penalty_enabled:
                penalty_cells = game.board.self_enclosed_cell_counts().get(player.id, 0)
                if penalty_cells:
                    suffixes.append(f"-{penalty_cells * constants.SELF_ENCLOSED_PENALTY_PER_CELL} enclosed")
            potential = game.potential_stats(player)
            if potential["area"]:
                suffixes.append(f"+{potential['area']} area")
            if game.prize_enabled and potential["prize_points"]:
                suffixes.append(f"+{potential['prize_points']} prize")
            if player.consecutive_skips:
                suffixes.append(f"skipped {player.consecutive_skips}/{game.skip_limit}")
            self._draw_score_row(x, y, player.id, primary, suffixes, TEXT_COLOR if active else MUTED_TEXT_COLOR)
            y += layout.PANEL_SCORE_ROW_HEIGHT

        self._divider(layout.PANEL_DIVIDER_2_Y)

        y = layout.PANEL_STATUS_Y
        if game.state == TurnState.AWAITING_ROLL:
            self._text("Your turn - roll the dice!", (x, y), self.font, MUTED_TEXT_COLOR)
            self._button(layout.ROLL_BUTTON_RECT, "Roll Dice (D)")
        elif game.state == TurnState.CHOOSING_WILDCARD:
            a, b = game.last_roll
            a_label = "*" if game.wildcard_index == 0 else str(a)
            b_label = "*" if game.wildcard_index == 1 else str(b)
            self._text(a_label, (x, y), self.font_dice, (0, 0, 0))
            self._text("x", (x + 30, y), self.font_dice)
            self._text(b_label, (x + 60, y), self.font_dice, (0, 0, 0))
            y += 36
            self._text("Pick a value for the wildcard number:", (x, y), self.font_small, MUTED_TEXT_COLOR)
            mouse_pos = self._mouse_pos
            for value, rect in layout.WILDCARD_VALUE_BUTTON_RECTS.items():
                legal = game.wildcard_value_is_legal(value)
                self._button(rect, str(value), enabled=legal, hovered=legal and rect.collidepoint(mouse_pos))
            if game.can_reroll():
                self._button(layout.REROLL_WILDCARD_BUTTON_RECT, self._reroll_label(game, short=True))
        elif game.state == TurnState.CHOOSING_PLACEMENT:
            a, b = game.last_roll
            w, h = ui_state.current_dims
            self._text(f"{a} x {b}", (x, y), self.font_dice)
            y += 36
            self._text(f"Placing {w}x{h} - click to place", (x, y), self.font_small, MUTED_TEXT_COLOR)
            self._button(layout.ROTATE_BUTTON_RECT, "Rotate (R)")
            if game.can_reroll():
                self._button(layout.REROLL_PLACEMENT_BUTTON_RECT, self._reroll_label(game))
        elif game.state == TurnState.SKIPPED:
            a, b = game.last_roll
            self._text(f"{a} x {b}", (x, y), self.font_dice)
            y += 36
            if game.can_reroll():
                self._text("No legal placement - reroll or skip", (x, y), self.font_small, (170, 40, 40))
                self._button(layout.REROLL_SKIPPED_BUTTON_RECT, self._reroll_label(game))
                self._button(layout.SKIP_BUTTON_RECT, "Skip (Space)")
            else:
                self._text("No legal placement - turn skipped", (x, y), self.font_small, (170, 40, 40))
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
            swatch = pygame.Rect(x, y + 3, 10, 10)
            pygame.draw.rect(self.screen, constants.PLAYER_COLORS[record.player_id], swatch)
            line = self._format_turn_caption(game, record)
            self._text(line, (x + 16, y), self.font_small, MUTED_TEXT_COLOR)
            y += layout.PANEL_HISTORY_ROW_HEIGHT

        if has_more:
            self._text("scroll for more ▼", (x, y), self.font_small, MUTED_TEXT_COLOR)

    def _format_turn_caption(self, game: Game, record: TurnRecord) -> str:
        player = game.players[record.player_id]
        if record.placed is not None:
            line = f"{player.name} placed {record.placed.width}x{record.placed.height}"
        else:
            a, b = record.roll
            line = f"{player.name} skipped (rolled {a},{b})"
        if record.wildcard_original_roll is not None:
            oa, ob = record.wildcard_original_roll
            line += f" (wildcard: rolled {oa},{ob})"
        return line

    def _round_row(self, series: Series, index: int, result: RoundResult) -> list[str]:
        row = [str(index), str(result.total[constants.PLAYER_1])]
        if series.prize_enabled:
            row.append(str(result.prize_captured[constants.PLAYER_1]))
        row.append(str(result.total[constants.PLAYER_2]))
        if series.prize_enabled:
            row.append(str(result.prize_captured[constants.PLAYER_2]))
        return row

    def _series_totals_row(self, series: Series) -> list[str]:
        row = ["Total", str(series.scores[constants.PLAYER_1])]
        if series.prize_enabled:
            row.append(str(series.total_prize_captured(constants.PLAYER_1)))
        row.append(str(series.scores[constants.PLAYER_2]))
        if series.prize_enabled:
            row.append(str(series.total_prize_captured(constants.PLAYER_2)))
        return row

    def _series_table_rows(self, series: Series) -> list[list[str]]:
        rows = [self._round_row(series, index, result) for index, result in enumerate(series.rounds, start=1)]
        if series.rounds:
            rows.append(self._series_totals_row(series))
        return rows

    def _series_table_columns(self, series: Series, *, panel: bool) -> list[tuple[str, int]]:
        if series.prize_enabled:
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
