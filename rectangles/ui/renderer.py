from __future__ import annotations

import pygame

from .. import bot, constants, persistence
from ..board import Board
from ..game import Game, GameOverReason, TurnState
from ..models import Player, Rectangle, TurnRecord
from ..series import RoundResult, Series
from ..tournament import Bracket
from . import layout
from .state import ConfirmAction, Screen, UIState

# A restrained indigo/emerald palette (Tailwind-ish) replaces the old flat
# purple-everywhere scheme: BUTTON_COLOR is reserved for primary actions,
# selection groups use the "outline" chip style below (neutral until
# selected) instead of painting every choice the same loud accent.
BG_COLOR = (246, 247, 250)
GRID_LINE_COLOR = (222, 224, 230)
EMPTY_CELL_COLOR = (255, 255, 255)
PANEL_BG_COLOR = (237, 238, 243)
TEXT_COLOR = (24, 28, 38)
MUTED_TEXT_COLOR = (108, 116, 132)
GHOST_LEGAL_COLOR = (80, 200, 120, 150)
GHOST_ILLEGAL_COLOR = (220, 70, 70, 130)
COVERABLE_CELL_COLOR = (190, 235, 200, 130)
BUTTON_COLOR = (79, 70, 229)
BUTTON_HOVER_COLOR = (99, 102, 241)
BUTTON_DISABLED_COLOR = (223, 225, 231)
BUTTON_DISABLED_TEXT_COLOR = (156, 161, 173)
BUTTON_SELECTED_COLOR = (5, 150, 105)
BUTTON_TEXT_COLOR = (255, 255, 255)
# "Outline" chip style for selection groups (board size, house rules, etc.):
# neutral until hovered/selected, so a row of choices reads calm rather than
# as a wall of accent color.
BUTTON_OUTLINE_BG_COLOR = (255, 255, 255)
BUTTON_OUTLINE_BORDER_COLOR = (211, 214, 222)
BUTTON_OUTLINE_TEXT_COLOR = (51, 56, 69)
BUTTON_OUTLINE_HOVER_BG_COLOR = (237, 237, 253)
OVERLAY_COLOR = (15, 15, 20, 190)
DIVIDER_COLOR = (222, 224, 230)
ROW_ACTIVE_BG_COLOR = (209, 250, 229)
CARD_BG_COLOR = (255, 255, 255)
CARD_BORDER_COLOR = (228, 229, 235)
CARD_SHADOW_COLOR = (15, 23, 42, 35)
FLAG_COLOR = (230, 180, 30)
WALL_LINE_COLOR = (90, 88, 96)
OBSTACLE_COLOR = (60, 60, 65)
LAST_MOVE_HIGHLIGHT_COLOR = (255, 225, 40)
STATUS_BANNER_BG_COLOR = (20, 20, 24, 215)
LETTERBOX_COLOR = (10, 10, 12)
ANALYSIS_WARNING_COLOR = (200, 70, 40)
ANALYSIS_SUGGESTION_COLOR = (60, 130, 220, 140)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        # Everything is drawn onto this fixed-size virtual canvas (see
        # layout.DESIGN_WIDTH/DESIGN_HEIGHT), then draw() scales the finished
        # canvas to fit whatever the real, freely-resizable window is.
        self._canvas = pygame.Surface((layout.DESIGN_WIDTH, layout.DESIGN_HEIGHT))
        # The settings screen's content can be taller than the canvas (see
        # layout.settings_content_height(mode) vs. DESIGN_HEIGHT); it's drawn
        # onto this full-height virtual surface and scrolled into view. Sized
        # for the tallest mode (Tournament) since this is allocated once,
        # before any mode is ever chosen - see SETTINGS_CONTENT_HEIGHT_MAX.
        self._settings_surface = pygame.Surface((layout.DESIGN_WIDTH, layout.SETTINGS_CONTENT_HEIGHT_MAX))
        # SysFont takes a comma-separated fallback list and picks the first
        # installed match, falling back to pygame's default font if none
        # resolve - safe across platforms (this project runs on macOS/Linux/
        # Windows dev machines and CI's dummy driver alike).
        _FONT_STACK = "segoeui,helveticaneue,helvetica,arial"
        self.font = pygame.font.SysFont(_FONT_STACK, 19)
        self.font_small = pygame.font.SysFont(_FONT_STACK, 15)
        self.font_big = pygame.font.SysFont(_FONT_STACK, 29, bold=True)
        self.font_dice = pygame.font.SysFont(_FONT_STACK, 28, bold=True)
        self._hand_cursor = False
        self._mouse_pos = (0, 0)
        self._turn_analyses_cache: (
            tuple[Game, int, dict[int, list[tuple[str, tuple[tuple[int, int], int, int] | None]]]] | None
        ) = None

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
        self.screen.fill(BG_COLOR)
        self._hand_cursor = False
        if ui_state.screen == Screen.MODE_SELECT:
            self._draw_mode_select_screen(ui_state)
        elif ui_state.screen == Screen.SETTINGS:
            self._settings_surface.fill(BG_COLOR)
            canvas, self.screen = self.screen, self._settings_surface
            self._draw_settings_screen(ui_state)
            self.screen = canvas
            visible = pygame.Rect(0, ui_state.settings_scroll, layout.DESIGN_WIDTH, layout.DESIGN_HEIGHT)
            self.screen.blit(self._settings_surface, (0, 0), area=visible)
            if ui_state.settings_scroll < layout.settings_max_scroll(ui_state.selected_game_mode, ui_state.tournament_size):
                # If scrolled content remains, this strip can sit over genuine
                # (clipped) content rather than blank space below it - mask it
                # first so the hint always reads cleanly instead of overlapping.
                strip = pygame.Rect(0, layout.DESIGN_HEIGHT - 26, layout.DESIGN_WIDTH, 26)
                self.screen.fill(BG_COLOR, strip)
                hint = self.font_small.render("scroll for more ▼", True, MUTED_TEXT_COLOR)
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
        self.screen.fill(LETTERBOX_COLOR)
        scaled_size = (round(layout.DESIGN_WIDTH * scale), round(layout.DESIGN_HEIGHT * scale))
        scaled_canvas = pygame.transform.smoothscale(self._canvas, scaled_size)
        self.screen.blit(scaled_canvas, (offset_x, offset_y))
        pygame.display.flip()

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
            # One unified 4-way choice (Human + 3 bot difficulties) replaces
            # the old separate vs-Bot toggle and Bot-difficulty rows.
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
        for label_text, enabled_flag in (
            ("Flags", ui_state.selected_flag_conquest_enabled),
            ("Walls", ui_state.selected_walls_enabled),
            ("Obstacles", ui_state.selected_obstacles_enabled),
            ("Wildcard", ui_state.selected_wildcard_enabled),
            ("Enclosure", ui_state.selected_self_enclosed_penalty_enabled),
            ("Reroll", ui_state.selected_reroll_enabled),
        ):
            rect = chip_rects[label_text]
            self._button(rect, label_text, selected=enabled_flag, hovered=hovered(rect), outline=True)

        start_label = {"Single": "Start Game (Space)", "Series": "Start Series (Space)", "Tournament": "Start Tournament (Space)"}[mode]
        start_rect = layout.settings_start_button_rect(mode, tournament_size)
        self._button(start_rect, start_label, hovered=hovered(start_rect))

        exit_rect = layout.settings_exit_button_rect(mode, tournament_size)
        self._button(exit_rect, "Exit (Esc)", hovered=hovered(exit_rect), outline=True)
        back_rect = layout.settings_back_button_rect(mode, tournament_size)
        self._button(back_rect, "Back", hovered=hovered(back_rect), outline=True)

    def _draw_grid_cells(self, game: Game) -> None:
        for r in range(game.board.size):
            for c in range(game.board.size):
                rect = layout.cell_rect(r, c, game.board.size)
                pygame.draw.rect(self.screen, EMPTY_CELL_COLOR, rect)
                pygame.draw.rect(self.screen, GRID_LINE_COLOR, rect, width=1)

    def _draw_board(self, game: Game) -> None:
        self._draw_grid_cells(game)

        self._draw_flags(game)
        self._draw_obstacles(game)

        for player in game.players.values():
            color = constants.PLAYER_COLORS[player.id]
            border = constants.PLAYER_BORDER_COLORS[player.id]
            for piece in player.pieces:
                rect = layout.piece_rect(piece.top_left, piece.width, piece.height, game.board.size)
                pygame.draw.rect(self.screen, color, rect)
                pygame.draw.rect(self.screen, border, rect, width=3)

        self._draw_last_move_highlight(game)
        self._draw_flag_capture_highlight(game)
        self._draw_walls(game)

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

    def _placed_upto(self, game: Game, step: int) -> list[Rectangle]:
        return [record.placed for record in game.history[:step] if record.placed is not None]

    def _draw_replay_board(self, game: Game, step: int) -> None:
        self._draw_grid_cells(game)

        self._draw_flags(game, upto=step)
        self._draw_obstacles(game)

        for rect in self._placed_upto(game, step):
            color = constants.PLAYER_COLORS[rect.owner]
            border = constants.PLAYER_BORDER_COLORS[rect.owner]
            piece_rect = layout.piece_rect(rect.top_left, rect.width, rect.height, game.board.size)
            pygame.draw.rect(self.screen, color, piece_rect)
            pygame.draw.rect(self.screen, border, piece_rect, width=3)

        self._draw_last_move_highlight(game, upto=step)
        self._draw_flag_capture_highlight(game, upto=step)
        self._draw_walls(game)

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

    def _last_placed_rect(self, game: Game, upto: int | None = None) -> Rectangle | None:
        history = game.history if upto is None else game.history[:upto]
        return next((record.placed for record in reversed(history) if record.placed is not None), None)

    def _draw_last_move_highlight(self, game: Game, upto: int | None = None) -> None:
        last_placed = self._last_placed_rect(game, upto)
        if last_placed is None:
            return
        rect = layout.piece_rect(
            last_placed.top_left, last_placed.width, last_placed.height, game.board.size
        ).inflate(4, 4)
        pygame.draw.rect(self.screen, LAST_MOVE_HIGHLIGHT_COLOR, rect, width=3)

    def _captured_flag_cells(self, game: Game, upto: int | None = None) -> frozenset[tuple[int, int]]:
        last_placed = self._last_placed_rect(game, upto)
        if last_placed is None:
            return frozenset()
        return game.board.flag_cells.intersection(last_placed.cells())

    def _draw_flag_capture_highlight(self, game: Game, upto: int | None = None) -> None:
        px = layout.cell_px(game.board.size)
        for r, c in self._captured_flag_cells(game, upto):
            center = layout.cell_rect(r, c, game.board.size).center
            pygame.draw.circle(self.screen, FLAG_COLOR, center, px // 2 - 5, width=4)

    def _new_scratch_board(self, game: Game) -> tuple[Board, dict[int, Player]]:
        board = Board(
            game.board.size,
            flag_cells=game.board.flag_cells,
            wall_edges=game.board.wall_edges,
            obstacle_cells=game.board.obstacle_cells,
        )
        scratch = {
            player_id: Player(player_id, "", game.players[player_id].start_corner) for player_id in game.players
        }
        return board, scratch

    def _board_at_step(self, game: Game, step: int) -> tuple[Board, dict[int, Player]]:
        board, scratch = self._new_scratch_board(game)
        for rect in self._placed_upto(game, step):
            board.place(scratch[rect.owner], rect.top_left, rect.width, rect.height)
        return board, scratch

    def _replay_stats(self, game: Game, step: int) -> dict[int, dict[str, int]]:
        stats = {player_id: {"area": 0, "flags": 0} for player_id in game.players}
        for rect in self._placed_upto(game, step):
            stats[rect.owner]["area"] += rect.area
            stats[rect.owner]["flags"] += len(game.board.flag_cells.intersection(rect.cells()))

        board, scratch = self._board_at_step(game, step)
        for player_id, player in scratch.items():
            reachable = board.reachable_empty_cells(player)
            stats[player_id]["potential_area"] = len(reachable)
            stats[player_id]["potential_flag_points"] = (
                len(reachable & board.flag_cells) * game.flag_bonus_points
            )
        return stats

    def _score_history(self, game: Game) -> dict[int, list[int]]:
        board, scratch = self._new_scratch_board(game)
        area = {player_id: 0 for player_id in game.players}
        flags = {player_id: 0 for player_id in game.players}
        history = {player_id: [0] for player_id in game.players}
        for record in game.history:
            if record.placed is not None:
                rect = record.placed
                board.place(scratch[rect.owner], rect.top_left, rect.width, rect.height)
                area[rect.owner] += rect.area
                flags[rect.owner] += len(game.board.flag_cells.intersection(rect.cells()))
            penalty = board.self_enclosed_cell_counts() if game.self_enclosed_penalty_enabled else {}
            for player_id in game.players:
                score = area[player_id] + flags[player_id] * game.flag_bonus_points
                score -= penalty.get(player_id, 0) * constants.SELF_ENCLOSED_PENALTY_PER_CELL
                history[player_id].append(score)
        return history

    def _turn_analyses(self, game: Game) -> dict[int, list[tuple[str, tuple[tuple[int, int], int, int] | None]]]:
        # Whole-game, one incremental O(N) walk (same shape as _score_history)
        # rather than N separate from-scratch board reconstructions - cached
        # below since this is the one case in Renderer where recompute-every-
        # frame is actually too expensive to skip a cache (unlike everywhere
        # else here, which is cheap enough to just redo each draw() call).
        # Cache key holds the actual game object (compared via `is`), not
        # id(game): an int id can be reused once an earlier game is garbage
        # collected, causing a false cache hit against an unrelated game -
        # holding a live reference here prevents that outright.
        if self._turn_analyses_cache is not None:
            cached_game, cached_history_len, cached_analyses = self._turn_analyses_cache
            if cached_game is game and cached_history_len == len(game.history):
                return cached_analyses

        board, scratch = self._new_scratch_board(game)
        analyses: dict[int, list[tuple[str, tuple[tuple[int, int], int, int] | None]]] = {}
        for step, record in enumerate(game.history, start=1):
            if record.placed is None:
                continue  # skips are never mistakes - no legal placement existed

            player = scratch[record.player_id]
            a, b = record.roll
            candidates = [
                (top_left, w, h)
                for w, h in ((a, b), (b, a))
                for top_left in board.legal_top_lefts(player, w, h)
            ]
            # A turn with only one legal option (forced move) was never a
            # choice, so it can't be flagged as a mistake - matters for
            # self-enclosure below, which (unlike flag/denial) doesn't
            # already fall out of the best-vs-chosen comparison.
            had_alternative = len(set(candidates)) > 1
            chosen = (record.placed.top_left, record.placed.width, record.placed.height)
            notes: list[tuple[str, tuple[tuple[int, int], int, int] | None]] = []

            if game.flag_conquest_enabled:
                chosen_score = bot.flag_score(chosen, board.flag_cells)
                best_candidate = max(candidates, key=lambda c: bot.flag_score(c, board.flag_cells))
                best_score = bot.flag_score(best_candidate, board.flag_cells)
                if best_score > chosen_score:
                    notes.append((f"missed flag capture (+{best_score - chosen_score} available)", best_candidate))

            opponent_id = constants.PLAYER_2 if record.player_id == constants.PLAYER_1 else constants.PLAYER_1
            opponent_frontier = board.frontier(scratch[opponent_id])
            chosen_score = bot.blocking_score(chosen, opponent_frontier)
            best_candidate = max(candidates, key=lambda c: bot.blocking_score(c, opponent_frontier))
            best_score = bot.blocking_score(best_candidate, opponent_frontier)
            if best_score > chosen_score:
                notes.append((f"missed denial (+{best_score - chosen_score} cells available)", best_candidate))

            if record.wildcard_original_roll is not None:
                fixed = record.wildcard_original_roll[0]
                chosen_value = b if a == fixed else a

                def best_for(value: int) -> tuple[int, tuple[tuple[int, int], int, int] | None]:
                    cands = [
                        (top_left, w, h)
                        for w, h in ((fixed, value), (value, fixed))
                        for top_left in board.legal_top_lefts(player, w, h)
                    ]
                    if not cands:
                        return 0, None
                    scored = [
                        (bot.flag_score(c, board.flag_cells) + bot.blocking_score(c, opponent_frontier), c)
                        for c in cands
                    ]
                    return max(scored, key=lambda sc: sc[0])

                results = {v: best_for(v) for v in range(constants.DICE_MIN, constants.DICE_MAX + 1)}
                chosen_score, _ = results[chosen_value]
                best_value, (best_score, best_candidate) = max(results.items(), key=lambda vb: vb[1][0])
                if best_score > chosen_score:
                    notes.append((
                        f"suboptimal wildcard pick (rolling {best_value} instead would score +{best_score - chosen_score})",
                        best_candidate,
                    ))

            before = board.self_enclosed_cell_counts().get(player.id, 0) if game.self_enclosed_penalty_enabled else 0
            board.place(player, record.placed.top_left, record.placed.width, record.placed.height)
            if game.self_enclosed_penalty_enabled:
                after = board.self_enclosed_cell_counts().get(player.id, 0)
                if after > before and had_alternative:
                    notes.append((f"created a {after - before}-cell self-enclosed hole", None))

            if notes:
                analyses[step] = notes

        self._turn_analyses_cache = (game, len(game.history), analyses)
        return analyses

    def _draw_turn_analysis(self, game: Game, step: int) -> None:
        y = layout.REPLAY_ANALYSIS_Y
        for message, _candidate in self._turn_analyses(game).get(step, []):
            y = self._draw_wrapped_text(
                f"! {message}", (layout.PANEL_X, y), self.font_small, layout.PANEL_CONTENT_WIDTH, ANALYSIS_WARNING_COLOR
            )

    def _draw_analysis_suggestions(self, game: Game, step: int, ui_state: UIState) -> None:
        if not ui_state.replay_show_better_option:
            return
        for _message, candidate in self._turn_analyses(game).get(step, []):
            if candidate is None:
                continue
            top_left, w, h = candidate
            rect = layout.piece_rect(top_left, w, h, game.board.size)
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill(ANALYSIS_SUGGESTION_COLOR)
            self.screen.blit(overlay, rect.topleft)
            pygame.draw.rect(self.screen, ANALYSIS_SUGGESTION_COLOR[:3], rect, width=2)

    def _draw_score_chart(self, game: Game, ui_state: UIState) -> None:
        x = layout.PANEL_X
        self._text("SCORE HISTORY", (x, layout.REPLAY_SCORE_CHART_LABEL_Y), self.font_small, MUTED_TEXT_COLOR)

        rect = layout.REPLAY_SCORE_CHART_RECT
        pygame.draw.rect(self.screen, CARD_BG_COLOR, rect, border_radius=6)
        pygame.draw.rect(self.screen, CARD_BORDER_COLOR, rect, width=1, border_radius=6)

        steps = len(game.history)
        if steps == 0:
            return

        history = self._score_history(game)
        all_scores = [score for series in history.values() for score in series]
        lo, hi = min(0, min(all_scores)), max(all_scores)
        if hi == lo:
            hi = lo + 1

        inner = rect.inflate(-16, -16)

        def point(step: int, score: int) -> tuple[int, int]:
            px = inner.left + round(step / steps * inner.width)
            py = inner.bottom - round((score - lo) / (hi - lo) * inner.height)
            return px, py

        for player_id, series in history.items():
            points = [point(step, score) for step, score in enumerate(series)]
            pygame.draw.lines(self.screen, constants.PLAYER_COLORS[player_id], False, points, width=2)

        for step in self._turn_analyses(game):
            player_id = game.history[step - 1].player_id
            pygame.draw.circle(self.screen, ANALYSIS_WARNING_COLOR, point(step, history[player_id][step]), 4)

        marker_x = inner.left + round(ui_state.replay_step / steps * inner.width)
        pygame.draw.line(self.screen, MUTED_TEXT_COLOR, (marker_x, inner.top), (marker_x, inner.bottom))

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

    def _status_banner_message(self, game: Game) -> str | None:
        if game.state == TurnState.CHOOSING_WILDCARD:
            return f"Wildcard roll! {game.current_player.name} may change one number"
        if game.state == TurnState.SKIPPED:
            return f"{game.current_player.name} skipped - no legal placement!"
        return None

    def _draw_status_banner(self, game: Game) -> None:
        message = self._status_banner_message(game)
        if message is None:
            return
        text_surf = self.font.render(message, True, (255, 255, 255))
        banner_rect = text_surf.get_rect().inflate(48, 28)
        # Centered on the full board square (not just the current board_size's
        # smaller rect), so it stays on-screen and in the same spot regardless
        # of which board size is selected.
        banner_rect.center = (layout.BOARD_PX // 2, layout.BOARD_PX // 2)
        overlay = pygame.Surface(banner_rect.size, pygame.SRCALPHA)
        overlay.fill(STATUS_BANNER_BG_COLOR)
        self.screen.blit(overlay, banner_rect.topleft)
        pygame.draw.rect(self.screen, LAST_MOVE_HIGHLIGHT_COLOR, banner_rect, width=2, border_radius=8)
        self.screen.blit(text_surf, text_surf.get_rect(center=banner_rect.center))

    def _draw_walls(self, game: Game) -> None:
        size = game.board.size
        px = layout.cell_px(size)
        for edge in game.board.wall_edges:
            a, b = tuple(edge)
            (r1, c1), (r2, c2) = (a, b) if a <= b else (b, a)
            if r1 == r2:
                # Horizontally adjacent cells (c1 < c2): vertical boundary line between them.
                x = layout.cell_rect(r1, c2, size).left
                top = layout.cell_rect(r1, c1, size).top
                pygame.draw.line(self.screen, WALL_LINE_COLOR, (x, top), (x, top + px), width=4)
            else:
                # Vertically adjacent cells (r1 < r2): horizontal boundary line between them.
                y = layout.cell_rect(r2, c1, size).top
                left = layout.cell_rect(r1, c1, size).left
                pygame.draw.line(self.screen, WALL_LINE_COLOR, (left, y), (left + px, y), width=4)

    def _draw_flags(self, game: Game, upto: int | None = None) -> None:
        covered = (
            None if upto is None else {cell for rect in self._placed_upto(game, upto) for cell in rect.cells()}
        )
        px = layout.cell_px(game.board.size)
        for r, c in game.board.flag_cells:
            is_covered = (r, c) in covered if covered is not None else game.board.owner_at(r, c) is not None
            if is_covered:
                continue
            cx, cy = layout.cell_rect(r, c, game.board.size).center
            half = px // 4
            points = [(cx - half, cy - half), (cx - half, cy + half), (cx + half, cy)]
            pygame.draw.polygon(self.screen, FLAG_COLOR, points)

    def _draw_obstacles(self, game: Game) -> None:
        for r, c in game.board.obstacle_cells:
            pygame.draw.rect(self.screen, OBSTACLE_COLOR, layout.cell_rect(r, c, game.board.size))

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

        px = layout.cell_px(game.board.size)
        overlay = pygame.Surface((px, px), pygame.SRCALPHA)
        overlay.fill(COVERABLE_CELL_COLOR)
        for r, c in covered:
            self.screen.blit(overlay, layout.cell_rect(r, c, game.board.size).topleft)

    def _draw_ghost(self, ui_state: UIState, board_size: int) -> None:
        w, h = ui_state.current_dims
        rect = layout.piece_rect(ui_state.hover_top_left, w, h, board_size)
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
        outline: bool = False,
    ) -> None:
        """outline=True is the "chip" style for a selection group (board
        size, house rules, opponent, ...): neutral/bordered until hovered or
        selected, so a row of choices doesn't read as a wall of accent
        color. outline=False (the default) is the solid-accent "primary
        action" style (Start, Roll, Continue, ...) - unchanged from before."""
        if enabled and rect.collidepoint(self._mouse_pos):
            self._hand_cursor = True
        border_color = None
        if not enabled:
            bg = BUTTON_DISABLED_COLOR
            text_color = BUTTON_DISABLED_TEXT_COLOR
        elif selected:
            bg = BUTTON_SELECTED_COLOR
            text_color = BUTTON_TEXT_COLOR
        elif outline:
            bg = BUTTON_OUTLINE_HOVER_BG_COLOR if hovered else BUTTON_OUTLINE_BG_COLOR
            text_color = BUTTON_COLOR if hovered else BUTTON_OUTLINE_TEXT_COLOR
            border_color = BUTTON_COLOR if hovered else BUTTON_OUTLINE_BORDER_COLOR
        else:
            bg = BUTTON_HOVER_COLOR if hovered else BUTTON_COLOR
            text_color = BUTTON_TEXT_COLOR
        pygame.draw.rect(self.screen, bg, rect, border_radius=8)
        if border_color is not None:
            pygame.draw.rect(self.screen, border_color, rect, width=1, border_radius=8)
        text = self.font.render(label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _draw_card(self, rect: pygame.Rect, radius: int = 12, shadow: bool = True) -> None:
        """A white, softly-shadowed panel - the "elevated card" look used by
        the settings screen and the confirm dialog, replacing flat
        border-only boxes."""
        if shadow:
            shadow_surf = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, CARD_SHADOW_COLOR, shadow_surf.get_rect(), border_radius=radius + 2)
            self.screen.blit(shadow_surf, (rect.x - 4, rect.y - 1))
        pygame.draw.rect(self.screen, CARD_BG_COLOR, rect, border_radius=radius)
        pygame.draw.rect(self.screen, CARD_BORDER_COLOR, rect, width=1, border_radius=radius)

    def _text(self, text: str, pos: tuple[int, int], font=None, color=TEXT_COLOR) -> None:
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
        self, text: str, pos: tuple[int, int], font, max_width: int, color: tuple[int, int, int] = TEXT_COLOR
    ) -> int:
        x, y = pos
        for line in self._wrap_text(text, font, max_width):
            self._text(line, (x, y), font, color)
            y += font.get_linesize()
        return y

    def _divider(self, y: int) -> None:
        pygame.draw.line(
            self.screen, DIVIDER_COLOR, (layout.PANEL_X, y), (layout.PANEL_X + layout.PANEL_CONTENT_WIDTH, y)
        )

    def _reroll_label(self, game: Game, short: bool = False) -> str:
        remaining = constants.REROLL_LIMIT - game.current_player.rerolls_used
        if short:
            return f"R{remaining}"
        return f"Reroll ({remaining}/{constants.REROLL_LIMIT})"

    def _draw_score_row(
        self, x: int, y: int, player_id: int, primary: str, suffixes: list[str], color: tuple[int, int, int]
    ) -> None:
        swatch = pygame.Rect(x, y + 2, 18, 18)
        pygame.draw.rect(self.screen, constants.PLAYER_COLORS[player_id], swatch)
        self._text(primary, (x + 26, y), self.font, color)
        if suffixes:
            self._text(
                "  ".join(suffixes), (x + 26, y + layout.PANEL_SCORE_LINE2_DY), self.font_small, MUTED_TEXT_COLOR
            )

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
            if player.flags_captured:
                primary += f"  F{player.flags_captured}"

            suffixes = []
            if game.self_enclosed_penalty_enabled:
                penalty_cells = game.board.self_enclosed_cell_counts().get(player.id, 0)
                if penalty_cells:
                    suffixes.append(f"-{penalty_cells * constants.SELF_ENCLOSED_PENALTY_PER_CELL} enclosed")
            potential = game.potential_stats(player)
            if potential["area"]:
                suffixes.append(f"+{potential['area']} area")
            if game.flag_conquest_enabled and potential["flag_points"]:
                suffixes.append(f"+{potential['flag_points']} flag")
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
            self._text(f"{a} x {b}", (x, y), self.font_dice)
            y += 36
            w, h = ui_state.current_dims
            self._text(f"Placing: {w} x {h}", (x, y))
            y += 26
            self._text("Click the board to place", (x, y), self.font_small, MUTED_TEXT_COLOR)
            self._button(layout.ROTATE_BUTTON_RECT, "Rotate (R)")
            if game.can_reroll():
                self._button(layout.REROLL_PLACEMENT_BUTTON_RECT, self._reroll_label(game))
        elif game.state == TurnState.SKIPPED:
            a, b = game.last_roll
            self._text(f"{a} x {b}", (x, y), self.font_dice)
            y += 36
            self._text("No legal placement", (x, y), self.font, (170, 40, 40))
            y += 24
            if game.can_reroll():
                self._text("for this roll.", (x, y), self.font_small, MUTED_TEXT_COLOR)
                self._button(layout.REROLL_SKIPPED_BUTTON_RECT, self._reroll_label(game))
                self._button(layout.SKIP_BUTTON_RECT, "Skip (Space)")
            else:
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
            swatch = pygame.Rect(x, y + 3, 10, 10)
            pygame.draw.rect(self.screen, constants.PLAYER_COLORS[record.player_id], swatch)
            line = self._format_turn_caption(game, record)
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

    def _draw_replay(self, game: Game, ui_state: UIState) -> None:
        step = ui_state.replay_step

        self._draw_replay_board(game, step)
        self._draw_analysis_suggestions(game, step, ui_state)

        pygame.draw.rect(self.screen, PANEL_BG_COLOR, layout.PANEL_RECT)
        x = layout.PANEL_X
        self._text("REPLAY", (x, layout.PANEL_HEADER_Y), self.font_big)
        self._text(
            f"Step {step} / {len(game.history)}",
            (x, layout.PANEL_HEADER_Y + 34),
            self.font_small,
            MUTED_TEXT_COLOR,
        )
        self._divider(layout.PANEL_DIVIDER_1_Y)

        y = layout.PANEL_SCORE_Y
        stats = self._replay_stats(game, step)
        for player in game.players.values():
            s = stats[player.id]
            primary = f"{player.name}: {s['area']}"
            if game.flag_conquest_enabled:
                primary += f"  F{s['flags']}"

            suffixes = []
            if s["potential_area"]:
                suffixes.append(f"+{s['potential_area']} area")
            if game.flag_conquest_enabled and s["potential_flag_points"]:
                suffixes.append(f"+{s['potential_flag_points']} flag")
            self._draw_score_row(x, y, player.id, primary, suffixes, TEXT_COLOR)
            y += layout.PANEL_SCORE_ROW_HEIGHT
        self._divider(layout.PANEL_DIVIDER_2_Y)

        if step == 0:
            caption = "Initial board"
        else:
            record = game.history[step - 1]
            caption = self._format_turn_caption(game, record)
            if record.placed is not None:
                r, c = record.placed.top_left
                caption += f" at ({r},{c})"
        self._draw_wrapped_text(caption, (x, layout.PANEL_STATUS_Y), self.font, layout.PANEL_CONTENT_WIDTH)
        self._draw_turn_analysis(game, step)

        self._draw_score_chart(game, ui_state)

        rects = layout.REPLAY_BUTTON_RECTS
        self._button(rects["first"], "|< First", enabled=step > 0)
        self._button(rects["prev"], "< Prev", enabled=step > 0)
        self._button(rects["next"], "Next >", enabled=step < len(game.history))
        self._button(rects["last"], "Last >|", enabled=step < len(game.history))
        self._button(
            rects["play"], "Pause" if ui_state.replay_autoplay else "Play", selected=ui_state.replay_autoplay
        )
        for value in constants.REPLAY_SPEED_PRESETS:
            self._button(rects[value], value, selected=ui_state.replay_speed == value)
        self._button(rects["back"], "Back (Esc)")

        self._button(
            layout.REPLAY_REVEAL_BUTTON_RECT,
            "Hide Better Option" if ui_state.replay_show_better_option else "Show Better Option",
            selected=ui_state.replay_show_better_option,
        )

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
