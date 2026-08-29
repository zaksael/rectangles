from __future__ import annotations

import pygame

from .. import bot, constants
from ..board import Board
from ..game import Game
from ..models import Player, Rectangle, TurnRecord
from . import colors, layout
from .state import UIState

# (wildcard value used, or None) + (top_left, width, height) - one candidate
# placement a turn's analysis can compare against the move actually played.
_AnalysisCandidate = tuple[tuple[int, int], int, int]
_AnalysisEntry = tuple[int | None, _AnalysisCandidate]


class ReplayMixin:
    def _placed_upto(self, game: Game, step: int) -> list[Rectangle]:
        return [record.placed for record in game.history[:step] if record.placed is not None]

    def _draw_replay_board(self, game: Game, step: int) -> None:
        self._draw_grid_cells(game)

        self._draw_flags(game, upto=step)
        self._draw_negative_cells(game, upto=step)
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
            negative_cells=game.board.negative_cells,
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

    def _candidate_partial_value(
        self,
        game: Game,
        board: Board,
        player: Player,
        candidate: tuple[tuple[int, int], int, int],
        opponent: Player,
        reachable_before: int,
    ) -> tuple[int, int]:
        # The two axes that are always computed for every candidate, whether
        # or not that candidate ends up worth paying for the (possibly
        # skipped) enclosure flood-fill. Denial is a reachable-area cutoff,
        # not just immediate-frontier overlap - see reachable_count_if's
        # docstring for why - and unlike frontier overlap, it has no cheap
        # exact bound, so it's always paid, never pruned.
        top_left, w, h = candidate
        flag_cells = bot.flag_score(candidate, board.flag_cells) if game.flag_conquest_enabled else 0
        denial_cells = reachable_before - board.reachable_count_if(player.id, opponent, top_left, w, h)
        return flag_cells, denial_cells

    def _candidate_value(
        self,
        game: Game,
        board: Board,
        player: Player,
        candidate: tuple[tuple[int, int], int, int],
        flag_cells: int,
        denial_cells: int,
        enclosure_before: int,
    ) -> tuple[int, int, int, int]:
        # One combined turn-quality value per candidate, using the same
        # point weights Game.total_score() applies - flag_bonus_points and
        # SELF_ENCLOSED_PENALTY_PER_CELL - so every candidate this turn is
        # ranked on one scale instead of separate flag/denial/enclosure
        # axes. Denial itself carries weight 1 (it has no total_score()
        # equivalent to borrow a weight from). flag_cells/denial_cells come
        # in pre-computed (via _candidate_partial_value) rather than
        # recomputed here, so a candidate that reaches this point never pays
        # for reachable_count_if twice. Returns the raw per-axis cell counts
        # alongside the total so a caller can name whichever axis actually
        # drove a gap between two candidates.
        enclosure_delta = 0
        if game.self_enclosed_penalty_enabled:
            top_left, w, h = candidate
            enclosure_delta = board.self_enclosed_count_if(player.id, top_left, w, h) - enclosure_before
        total = (
            flag_cells * game.flag_bonus_points
            + denial_cells
            - enclosure_delta * constants.SELF_ENCLOSED_PENALTY_PER_CELL
        )
        return total, flag_cells, denial_cells, enclosure_delta

    def _analysis_candidate_pool(
        self, record: TurnRecord, board: Board, player: Player
    ) -> tuple[int | None, list[_AnalysisEntry]]:
        # Candidate pool spans every reachable (value, placement) pair this
        # turn could have used - just the rolled orientation pair normally,
        # or every possible wildcard value on a Wildcard Roll turn (still one
        # pool, one comparison, one note either way).
        a, b = record.roll
        if record.wildcard_original_roll is not None:
            fixed = record.wildcard_original_roll[0]
            chosen_value: int | None = b if a == fixed else a
            pool = [
                (value, (top_left, w, h))
                for value in range(constants.DICE_MIN, constants.DICE_MAX + 1)
                for w, h in ((fixed, value), (value, fixed))
                for top_left in board.legal_top_lefts(player, w, h)
            ]
        else:
            chosen_value = None
            pool = [
                (None, (top_left, w, h))
                for w, h in ((a, b), (b, a))
                for top_left in board.legal_top_lefts(player, w, h)
            ]
        return chosen_value, pool

    def _best_analysis_candidate(
        self,
        game: Game,
        board: Board,
        player: Player,
        opponent: Player,
        reachable_before: int,
        enclosure_before: int,
        pool: list[_AnalysisEntry],
    ) -> tuple[float, _AnalysisEntry, int, int, int]:
        # self_enclosed_count_if is an O(board_size^2) flood-fill; a
        # Wildcard Roll turn's pool can run into the hundreds on a large
        # board, and running it for every candidate made replay's first
        # screen switch visibly laggy. A count can never go negative, so
        # a candidate's enclosure bonus is capped at enclosure_before
        # (fully clearing every already-enclosed cell) - its total can
        # never exceed its cheap flag+denial value plus that ceiling.
        # Skip the flood-fill for any candidate that ceiling can't lift
        # past the running best; only the few genuinely competitive
        # candidates ever pay for it. Provably exact, not a heuristic:
        # a skipped candidate could never have won anyway.
        # ponytail: this ceiling is player-wide (all of enclosure_before,
        # not just the region(s) a given candidate actually touches), so
        # it stops pruning much once a player has several existing
        # self-enclosed cells - deep games on the largest board with
        # both Wildcard and Enclosure Penalty on can still take ~1s
        # (measured), down from ~3s unpruned. A tighter, region-scoped
        # bound (or an incremental region tracker instead of a fresh
        # flood-fill per candidate) would close the rest of the gap if
        # that's ever felt as too slow.
        ceiling_bonus = (
            enclosure_before * constants.SELF_ENCLOSED_PENALTY_PER_CELL if game.self_enclosed_penalty_enabled else 0
        )
        # pool always contains at least the chosen move (it was legally
        # placed under this same roll), so the first iteration always
        # runs and sets real values below - a float("-inf") seed needs
        # no is-None checks, unlike a None seed would.
        best_value_axis = float("-inf")
        for entry in pool:
            _, candidate = entry
            flag_cells, denial_cells = self._candidate_partial_value(
                game, board, player, candidate, opponent, reachable_before
            )
            partial = flag_cells * game.flag_bonus_points + denial_cells
            if partial + ceiling_bonus <= best_value_axis:
                continue
            total, flag_cells, denial_cells, enclosure_delta = self._candidate_value(
                game, board, player, candidate, flag_cells, denial_cells, enclosure_before
            )
            if total > best_value_axis:
                best_value_axis, best_flag, best_denial, best_enclosure = total, flag_cells, denial_cells, enclosure_delta
                best_entry = entry
        return best_value_axis, best_entry, best_flag, best_denial, best_enclosure

    def _analysis_note(
        self,
        game: Game,
        chosen_value: int | None,
        chosen_total: int,
        chosen_flag: int,
        chosen_denial: int,
        chosen_enclosure: int,
        best_value_axis: float,
        best_entry: _AnalysisEntry,
        best_flag: int,
        best_denial: int,
        best_enclosure: int,
    ) -> tuple[str, _AnalysisCandidate] | None:
        if best_value_axis <= chosen_total:
            return None
        best_die, best_candidate = best_entry
        if chosen_value is not None and best_die != chosen_value:
            return (
                f"suboptimal wildcard pick (rolling {best_die} instead would "
                f"score +{best_value_axis - chosen_total})",
                best_candidate,
            )
        flag_gap = (best_flag - chosen_flag) * game.flag_bonus_points if game.flag_conquest_enabled else 0
        denial_gap = best_denial - chosen_denial
        enclosure_gap = (
            (chosen_enclosure - best_enclosure) * constants.SELF_ENCLOSED_PENALTY_PER_CELL
            if game.self_enclosed_penalty_enabled
            else 0
        )
        _gap, message = max(
            (
                (flag_gap, f"missed flag capture (+{best_flag - chosen_flag} available)"),
                (denial_gap, f"missed denial (+{best_denial - chosen_denial} cells available)"),
                (
                    enclosure_gap,
                    f"would have avoided creating a {chosen_enclosure - best_enclosure}-cell "
                    "self-enclosed hole",
                ),
            ),
            key=lambda gm: gm[0],
        )
        return (message, best_candidate)

    def _turn_analyses(self, game: Game) -> dict[int, tuple[str, _AnalysisCandidate]]:
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
        analyses: dict[int, tuple[str, _AnalysisCandidate]] = {}
        for step, record in enumerate(game.history, start=1):
            if record.placed is None:
                continue  # skips are never mistakes - no legal placement existed

            player = scratch[record.player_id]
            opponent_id = constants.PLAYER_2 if record.player_id == constants.PLAYER_1 else constants.PLAYER_1
            opponent = scratch[opponent_id]
            reachable_before = len(board.reachable_empty_cells(opponent))
            enclosure_before = (
                board.self_enclosed_cell_counts().get(player.id, 0) if game.self_enclosed_penalty_enabled else 0
            )

            chosen_value, pool = self._analysis_candidate_pool(record, board, player)
            chosen_candidate = (record.placed.top_left, record.placed.width, record.placed.height)
            chosen_partial_flag, chosen_partial_denial = self._candidate_partial_value(
                game, board, player, chosen_candidate, opponent, reachable_before
            )
            chosen_total, chosen_flag, chosen_denial, chosen_enclosure = self._candidate_value(
                game, board, player, chosen_candidate, chosen_partial_flag, chosen_partial_denial, enclosure_before
            )
            best_value_axis, best_entry, best_flag, best_denial, best_enclosure = self._best_analysis_candidate(
                game, board, player, opponent, reachable_before, enclosure_before, pool
            )

            note = self._analysis_note(
                game,
                chosen_value,
                chosen_total,
                chosen_flag,
                chosen_denial,
                chosen_enclosure,
                best_value_axis,
                best_entry,
                best_flag,
                best_denial,
                best_enclosure,
            )
            if note is not None:
                analyses[step] = note

            board.place(player, record.placed.top_left, record.placed.width, record.placed.height)

        self._turn_analyses_cache = (game, len(game.history), analyses)
        return analyses

    def _draw_turn_analysis(self, game: Game, step: int) -> None:
        note = self._turn_analyses(game).get(step)
        if note is not None:
            message, _candidate = note
            self._draw_wrapped_text(
                f"! {message}", (layout.PANEL_X, layout.REPLAY_ANALYSIS_Y), self.font_small,
                layout.PANEL_CONTENT_WIDTH, colors.ANALYSIS_WARNING_COLOR,
            )

    def _draw_analysis_suggestions(self, game: Game, step: int, ui_state: UIState) -> None:
        if not ui_state.replay_show_better_option:
            return
        note = self._turn_analyses(game).get(step)
        if note is None:
            return
        _message, candidate = note
        if candidate is None:
            return
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
