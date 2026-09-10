from __future__ import annotations

import pygame

from . import layout
from .colors import MUTED_TEXT_COLOR, TEXT_COLOR
from .state import UIState


class SettingsMixin:
    def _draw_settings_screen(self, ui_state: UIState) -> None:
        center_x = layout.DESIGN_WIDTH // 2
        mouse_pos = self._mouse_pos
        mode = ui_state.selected_game_mode

        def hovered(rect: pygame.Rect) -> bool:
            return rect.collidepoint(mouse_pos)

        title_surf = self.font_big.render("RECTANGLES", True, TEXT_COLOR)
        self.screen.blit(title_surf, title_surf.get_rect(center=(center_x, 56)))
        subtitle_surf = self.font.render(f"{mode} - choose your settings", True, MUTED_TEXT_COLOR)
        self.screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(center_x, 96)))

        tournament_size = ui_state.tournament_size

        def row_label(row_id: str, text: str, font: pygame.font.Font | None = None) -> None:
            top = layout.settings_row_top(mode, tournament_size, row_id)
            label_surf = (font or self.font).render(text, True, TEXT_COLOR)
            self.screen.blit(
                label_surf, label_surf.get_rect(midleft=(layout.SETTINGS_FORM_LABEL_X, top + layout.SETTINGS_ROW_H // 2))
            )

        row_label("board_size", "Board size")
        for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
            self._button(
                rect, f"{value}x{value}", selected=value == ui_state.selected_board_size, hovered=hovered(rect), outline=True
            )

        row_label("skip_limit", "Skip limit")
        for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
            self._button(
                rect, str(value), selected=value == ui_state.selected_skip_limit, hovered=hovered(rect), outline=True
            )

        if mode != "Tournament":
            # One 4-way choice: Human + 3 bot difficulties.
            row_label("opponent", "Opponent (P2)")
            current = ui_state.selected_bot_difficulty if ui_state.selected_bot_enabled else "Human"
            for value, rect in layout.settings_opponent_button_rects(mode, tournament_size).items():
                self._button(rect, value, selected=value == current, hovered=hovered(rect), outline=True)

        if mode != "Single":
            row_label("series_length", "Series Length")
            for value, rect in layout.settings_series_length_button_rects(mode, tournament_size).items():
                self._button(
                    rect,
                    f"{value} Rounds",
                    selected=value == ui_state.selected_series_length,
                    hovered=hovered(rect),
                    outline=True,
                )

        if mode == "Tournament":
            row_label("tournament_size", "Tournament size")
            for value, rect in layout.settings_tournament_size_button_rects(tournament_size).items():
                self._button(
                    rect, f"{value} Players", selected=value == ui_state.tournament_size, hovered=hovered(rect), outline=True
                )
            for i in range(tournament_size):
                is_bot = ui_state.tournament_slot_is_bot[i]
                row_label(f"tournament_slot_{i}", f"Slot {i + 1}", font=self.font_small)
                toggle_rect = layout.settings_tournament_slot_toggle_rect(tournament_size, i)
                self._button(
                    toggle_rect, "Bot" if is_bot else "Human", selected=is_bot, hovered=hovered(toggle_rect), outline=True
                )
                for value, rect in layout.settings_tournament_slot_difficulty_rects(tournament_size, i).items():
                    self._button(
                        rect,
                        value,
                        enabled=is_bot,
                        selected=is_bot and value == ui_state.tournament_slot_difficulty[i],
                        hovered=is_bot and hovered(rect),
                        outline=True,
                    )

        house_rules_top = layout.settings_row_top(mode, tournament_size, "house_rules")
        house_rules_label = self.font.render("House Rules", True, TEXT_COLOR)
        self.screen.blit(house_rules_label, house_rules_label.get_rect(topleft=(layout.SETTINGS_FORM_LABEL_X, house_rules_top)))

        all_rules_rect = layout.settings_all_rules_button_rect(mode, tournament_size)
        self._button(
            all_rules_rect,
            "Turn All OFF" if ui_state.all_house_rules_enabled else "Turn All ON",
            hovered=hovered(all_rules_rect),
            outline=True,
        )

        chip_rects = layout.settings_house_rule_button_rects(mode, tournament_size)
        for label_text, is_selected in (
            ("Prize", ui_state.selected_prize_enabled),
            ("Walls", ui_state.selected_walls_enabled),
            ("Obstacles", ui_state.selected_obstacles_enabled),
            ("Pitfall", ui_state.selected_pitfall_enabled),
            ("Steal", ui_state.selected_steal_enabled),
            ("Wildcard", ui_state.selected_wildcard_enabled),
            ("Enclosure", ui_state.selected_self_enclosed_penalty_enabled),
            ("Reroll", ui_state.selected_reroll_enabled),
            ("Comeback", ui_state.selected_comeback_nudge_enabled),
        ):
            rect = chip_rects[label_text]
            self._button(rect, label_text, selected=is_selected, hovered=hovered(rect), outline=True)

        start_label = {"Single": "Start Game (Space)", "Series": "Start Series (Space)", "Tournament": "Start Tournament (Space)"}[mode]
        start_rect = layout.settings_start_button_rect(mode, tournament_size)
        self._button(start_rect, start_label, hovered=hovered(start_rect))

        exit_rect = layout.settings_exit_button_rect(mode, tournament_size)
        self._button(exit_rect, "Exit (Esc)", hovered=hovered(exit_rect), outline=True)
        back_rect = layout.settings_back_button_rect(mode, tournament_size)
        self._button(back_rect, "Back", hovered=hovered(back_rect), outline=True)
