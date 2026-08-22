from __future__ import annotations

import pygame

from .. import bot, constants
from ..board import Board
from ..game import Game
from ..models import Player, Rectangle
from . import colors, layout
from .state import UIState


class ReplayMixin:
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
                f"! {message}", (layout.PANEL_X, y), self.font_small, layout.PANEL_CONTENT_WIDTH, colors.ANALYSIS_WARNING_COLOR
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
            overlay.fill(colors.ANALYSIS_SUGGESTION_COLOR)
            self.screen.blit(overlay, rect.topleft)
            pygame.draw.rect(self.screen, colors.ANALYSIS_SUGGESTION_COLOR[:3], rect, width=2)

    def _draw_score_chart(self, game: Game, ui_state: UIState) -> None:
        x = layout.PANEL_X
        self._text("SCORE HISTORY", (x, layout.REPLAY_SCORE_CHART_LABEL_Y), self.font_small, colors.MUTED_TEXT_COLOR)

        rect = layout.REPLAY_SCORE_CHART_RECT
        pygame.draw.rect(self.screen, colors.CARD_BG_COLOR, rect, border_radius=6)
        pygame.draw.rect(self.screen, colors.CARD_BORDER_COLOR, rect, width=1, border_radius=6)

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
            pygame.draw.circle(self.screen, colors.ANALYSIS_WARNING_COLOR, point(step, history[player_id][step]), 4)

        marker_x = inner.left + round(ui_state.replay_step / steps * inner.width)
        pygame.draw.line(self.screen, colors.MUTED_TEXT_COLOR, (marker_x, inner.top), (marker_x, inner.bottom))

    def _draw_replay(self, game: Game, ui_state: UIState) -> None:
        step = ui_state.replay_step

        self._draw_replay_board(game, step)
        self._draw_analysis_suggestions(game, step, ui_state)

        pygame.draw.rect(self.screen, colors.PANEL_BG_COLOR, layout.PANEL_RECT)
        x = layout.PANEL_X
        self._text("REPLAY", (x, layout.PANEL_HEADER_Y), self.font_big)
        self._text(
            f"Step {step} / {len(game.history)}",
            (x, layout.PANEL_HEADER_Y + 34),
            self.font_small,
            colors.MUTED_TEXT_COLOR,
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
            self._draw_score_row(x, y, player.id, primary, suffixes, colors.TEXT_COLOR)
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
