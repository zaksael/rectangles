from __future__ import annotations

from ..engine.tournament import Bracket
from . import layout
from .colors import BUTTON_SELECTED_COLOR, MUTED_TEXT_COLOR, TEXT_COLOR


class TournamentMixin:
    def _draw_tournament(self, tournament: Bracket) -> None:
        center_x = layout.DESIGN_WIDTH // 2
        title_surf = self.font_big.render("TOURNAMENT BRACKET", True, TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(center_x, layout.TOURNAMENT_TITLE_Y)))

        total_rounds = len(tournament.participants).bit_length() - 1
        round_names = [f"Round {i + 1}" for i in range(total_rounds - 1)] + ["Final"]

        for round_index in range(total_rounds):
            column = layout.tournament_column_rect(round_index, total_rounds)
            header_surf = self.font.render(round_names[round_index], True, MUTED_TEXT_COLOR)
            self.screen.blit(header_surf, header_surf.get_rect(center=(column.centerx, column.top - 30)))

            if round_index < len(tournament.rounds):
                matches = tournament.rounds[round_index]
                for row, match in enumerate(matches):
                    a = tournament.participants[match.participant_a]
                    b = tournament.participants[match.participant_b]
                    line = f"{a.name}  vs  {b.name}"
                    color = TEXT_COLOR
                    if match.winner is not None:
                        winner_name = tournament.participants[match.winner].name
                        line += f"   →  {winner_name}"
                        color = BUTTON_SELECTED_COLOR
                    y = column.top + row * layout.TOURNAMENT_ROW_HEIGHT
                    self._draw_wrapped_text(line, (column.left, y), self.font_small, column.width, color)
            else:
                y = column.top
                self._text("TBD", (column.left, y), self.font_small, MUTED_TEXT_COLOR)

        if tournament.is_complete():
            champion = tournament.champion()
            label = f"Champion: {champion.name}"
            button_label = "New Tournament"
        elif tournament.current_match().series is None:
            played, total = self._tournament_match_number(tournament)
            label = f"Ready for match {played} of {total}"
            button_label = f"Begin Match {played}"
        else:
            label = "Tournament in progress"
            button_label = "Back"

        label_surf = self.font.render(label, True, TEXT_COLOR)
        self.screen.blit(label_surf, label_surf.get_rect(center=(center_x, layout.TOURNAMENT_ACTION_BUTTON_RECT.top - 30)))
        self._button(layout.TOURNAMENT_ACTION_BUTTON_RECT, button_label)
