from __future__ import annotations

import pygame

from .. import bot, constants
from ..board import Board
from ..constants import CellKind
from ..game import Game
from ..models import Player, Rectangle, TurnRecord
from . import colors, layout
from .state import UIState

# (top_left, width, height) - one candidate placement a turn's analysis can
# compare against the move actually played.
_AnalysisCandidate = tuple[tuple[int, int], int, int]

# (prize_cells, pitfall_cells, denial_cells, enclosure_delta) - one candidate's
# raw per-axis values, bundled so they thread through _candidate_value/
# _best_analysis_candidate/_analysis_note as a unit instead of four
# same-typed ints each (easy to transpose when passed individually).
_AxisBreakdown = tuple[int, int, int, int]


class ReplayMixin:
    def _placed_upto(self, game: Game, step: int) -> list[Rectangle]:
        return [record.placed for record in game.history[:step] if record.placed is not None]

    def _draw_replay_board(self, game: Game, step: int) -> None:
        self._draw_grid_cells(game)

        self._draw_prize_cells(game, upto=step)
        self._draw_pitfall_cells(game, upto=step)
        self._draw_obstacles(game)

        for rect in self._placed_upto(game, step):
            color = constants.PLAYER_COLORS[rect.owner]
            border = constants.PLAYER_BORDER_COLORS[rect.owner]
            piece_rect = layout.piece_rect(rect.top_left, rect.width, rect.height, game.board.size)
            pygame.draw.rect(self.screen, color, piece_rect)
            pygame.draw.rect(self.screen, border, piece_rect, width=3)

        self._draw_last_move_highlight(game, upto=step)
        self._draw_prize_capture_highlight(game, upto=step)
        self._draw_walls(game)

        pygame.draw.rect(self.screen, (150, 150, 150), layout.board_rect(game.board.size), width=2)

    def _new_scratch_board(self, game: Game) -> tuple[Board, dict[int, Player]]:
        board = Board(
            game.board.size,
            special_cells=game.board.special_cells,
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
        stats = {player_id: {"area": 0, "prizes": 0} for player_id in game.players}
        for rect in self._placed_upto(game, step):
            stats[rect.owner]["area"] += rect.area
            stats[rect.owner]["prizes"] += len(game.board.cells_of_kind(CellKind.PRIZE).intersection(rect.cells()))

        board, scratch = self._board_at_step(game, step)
        for player_id, player in scratch.items():
            reachable = board.reachable_empty_cells(player)
            stats[player_id]["potential_area"] = len(reachable)
            stats[player_id]["potential_prize_points"] = (
                len(reachable & board.cells_of_kind(CellKind.PRIZE)) * game.points_for(CellKind.PRIZE)
            )
        return stats

    def _score_history(self, game: Game) -> dict[int, list[int]]:
        board, scratch = self._new_scratch_board(game)
        area = {player_id: 0 for player_id in game.players}
        prizes = {player_id: 0 for player_id in game.players}
        pitfalls = {player_id: 0 for player_id in game.players}
        history = {player_id: [0] for player_id in game.players}
        for record in game.history:
            if record.placed is not None:
                rect = record.placed
                board.place(scratch[rect.owner], rect.top_left, rect.width, rect.height)
                area[rect.owner] += rect.area
                prizes[rect.owner] += len(game.board.cells_of_kind(CellKind.PRIZE).intersection(rect.cells()))
                pitfalls[rect.owner] += len(game.board.cells_of_kind(CellKind.PITFALL).intersection(rect.cells()))
            penalty = board.self_enclosed_cell_counts() if game.self_enclosed_penalty_enabled else {}
            for player_id in game.players:
                score = area[player_id] + prizes[player_id] * game.points_for(CellKind.PRIZE)
                score -= pitfalls[player_id] * game.points_for(CellKind.PITFALL)
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
    ) -> tuple[int, int, int]:
        # The axes that are always computed for every candidate, whether or
        # not that candidate ends up worth paying for the (possibly
        # skipped) enclosure flood-fill. Prize/pitfall are both cheap exact cell-
        # overlap counts (bot.cell_overlap_score is a generic counter, not
        # prize-specific). Denial is a
        # reachable-area cutoff, not just immediate-frontier overlap - see
        # reachable_count_if's docstring for why - and unlike frontier
        # overlap, it has no cheap exact bound, so it's always paid, never
        # pruned.
        top_left, w, h = candidate
        prize_cells = bot.cell_overlap_score(candidate, board.cells_of_kind(CellKind.PRIZE)) if game.prize_enabled else 0
        pitfall_cells = bot.cell_overlap_score(candidate, board.cells_of_kind(CellKind.PITFALL)) if game.pitfall_enabled else 0
        denial_cells = reachable_before - board.reachable_count_if(player.id, opponent, top_left, w, h)
        return prize_cells, pitfall_cells, denial_cells

    def _candidate_value(
        self,
        game: Game,
        board: Board,
        player: Player,
        candidate: tuple[tuple[int, int], int, int],
        prize_cells: int,
        pitfall_cells: int,
        denial_cells: int,
        enclosure_before: int,
    ) -> tuple[int, _AxisBreakdown]:
        # One combined turn-quality value per candidate, using the same
        # point weights Game.total_score() applies - game.points_for(PRIZE/PITFALL)
        # and SELF_ENCLOSED_PENALTY_PER_CELL -
        # so every candidate this turn is ranked on one scale instead of
        # separate prize/pitfall/denial/enclosure axes. Denial itself carries
        # weight 1 (it has no total_score() equivalent to borrow a weight
        # from) - this "total" is a ranking/threshold value only, never
        # shown to the player as if it were real score (see _analysis_note).
        # prize_cells/pitfall_cells/denial_cells come in pre-computed (via
        # _candidate_partial_value) rather than recomputed here, so a
        # candidate that reaches this point never pays for
        # reachable_count_if twice. Returns the raw per-axis breakdown
        # alongside the total so _analysis_note can report real score
        # points (prize/pitfall/enclosure) separately from the denial cell
        # count, and name whichever axis actually drove the gap.
        enclosure_delta = 0
        if game.self_enclosed_penalty_enabled:
            top_left, w, h = candidate
            enclosure_delta = board.self_enclosed_count_if(player.id, top_left, w, h) - enclosure_before
        total = (
            prize_cells * game.points_for(CellKind.PRIZE)
            - pitfall_cells * game.points_for(CellKind.PITFALL)
            + denial_cells
            - enclosure_delta * constants.SELF_ENCLOSED_PENALTY_PER_CELL
        )
        return total, (prize_cells, pitfall_cells, denial_cells, enclosure_delta)

    def _analysis_candidate_pool(
        self, record: TurnRecord, board: Board, player: Player
    ) -> list[_AnalysisCandidate]:
        # Candidate pool spans every reachable placement this turn could
        # have used - just the rolled orientation pair normally, or every
        # possible wildcard value's orientations on a Wildcard Roll turn
        # (still one pool, one comparison, one note either way). Which die
        # value produced which candidate isn't tracked - the note reports a
        # plain score comparison, not which specific choice caused it.
        a, b = record.roll
        if record.wildcard_original_roll is not None:
            fixed = record.wildcard_original_roll[0]
            return [
                (top_left, w, h)
                for value in range(constants.DICE_MIN, constants.DICE_MAX + 1)
                for w, h in ((fixed, value), (value, fixed))
                for top_left in board.legal_top_lefts(player, w, h)
            ]
        return [
            (top_left, w, h)
            for w, h in ((a, b), (b, a))
            for top_left in board.legal_top_lefts(player, w, h)
        ]

    def _best_analysis_candidate(
        self,
        game: Game,
        board: Board,
        player: Player,
        opponent: Player,
        reachable_before: int,
        enclosure_before: int,
        pool: list[_AnalysisCandidate],
    ) -> tuple[float, _AnalysisCandidate, _AxisBreakdown]:
        # self_enclosed_count_if is an O(board_size^2) flood-fill; a
        # Wildcard Roll turn's pool can run into the hundreds on a large
        # board, and running it for every candidate made replay's first
        # screen switch visibly laggy. A count can never go negative, so
        # a candidate's enclosure bonus is capped at enclosure_before
        # (fully clearing every already-enclosed cell) - its total can
        # never exceed its cheap prize+denial value plus that ceiling.
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
        for candidate in pool:
            prize_cells, pitfall_cells, denial_cells = self._candidate_partial_value(
                game, board, player, candidate, opponent, reachable_before
            )
            partial = (
                prize_cells * game.points_for(CellKind.PRIZE)
                - pitfall_cells * game.points_for(CellKind.PITFALL)
                + denial_cells
            )
            if partial + ceiling_bonus <= best_value_axis:
                continue
            total, breakdown = self._candidate_value(
                game, board, player, candidate, prize_cells, pitfall_cells, denial_cells, enclosure_before
            )
            if total > best_value_axis:
                best_value_axis = total
                best_breakdown = breakdown
                best_candidate = candidate
        return best_value_axis, best_candidate, best_breakdown

    def _analysis_note(
        self,
        game: Game,
        chosen_total: int,
        chosen_breakdown: _AxisBreakdown,
        best_value_axis: float,
        best_candidate: _AnalysisCandidate,
        best_breakdown: _AxisBreakdown,
    ) -> tuple[str, _AnalysisCandidate] | None:
        # Reports a plain actual-vs-best comparison, no computed delta - the
        # two raw values are enough to compare at a glance - but never as one
        # blended "score": denial carries no real total_score() weight (a
        # pure cell-count heuristic, see _candidate_value), so mixing it into
        # the same number as prize/pitfall/enclosure would mislabel a heuristic
        # as real points. Whichever axis actually drove the gap (same
        # weighted-gap comparison and tie order as before: prize > pitfall >
        # denial > enclosure) picks which pair of numbers to show and names
        # itself in a short label - "denied N cells" already names its own
        # axis, so only the points branch needs an explicit label suffix to
        # disambiguate prize/pitfall/enclosure from each other.
        if best_value_axis <= chosen_total:
            return None
        chosen_prize, chosen_pitfall, chosen_denial, chosen_enclosure = chosen_breakdown
        best_prize, best_pitfall, best_denial, best_enclosure = best_breakdown
        prize_gap = (best_prize - chosen_prize) * game.points_for(CellKind.PRIZE) if game.prize_enabled else 0
        pitfall_gap = (
            (chosen_pitfall - best_pitfall) * game.points_for(CellKind.PITFALL) if game.pitfall_enabled else 0
        )
        denial_gap = best_denial - chosen_denial
        enclosure_gap = (
            (chosen_enclosure - best_enclosure) * constants.SELF_ENCLOSED_PENALTY_PER_CELL
            if game.self_enclosed_penalty_enabled
            else 0
        )
        _gap, axis = max(
            ((prize_gap, "prize"), (pitfall_gap, "pitfall"), (denial_gap, "denial"), (enclosure_gap, "enclosure")),
            key=lambda ga: ga[0],
        )
        if axis == "denial":
            unit = "cell" if chosen_denial == 1 else "cells"
            message = f"denied {chosen_denial} {unit} this turn (best possible: {best_denial})"
        else:
            def points(prize: int, pitfall: int, enclosure: int) -> int:
                return (
                    prize * game.points_for(CellKind.PRIZE)
                    - pitfall * game.points_for(CellKind.PITFALL)
                    - enclosure * constants.SELF_ENCLOSED_PENALTY_PER_CELL
                )

            chosen_points = points(chosen_prize, chosen_pitfall, chosen_enclosure)
            best_points = points(best_prize, best_pitfall, best_enclosure)
            message = f"scored {chosen_points} this turn (best possible: {best_points} — {axis})"
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

            pool = self._analysis_candidate_pool(record, board, player)
            chosen_candidate = (record.placed.top_left, record.placed.width, record.placed.height)
            chosen_partial_prize, chosen_partial_pitfall, chosen_partial_denial = self._candidate_partial_value(
                game, board, player, chosen_candidate, opponent, reachable_before
            )
            chosen_total, chosen_breakdown = self._candidate_value(
                game,
                board,
                player,
                chosen_candidate,
                chosen_partial_prize,
                chosen_partial_pitfall,
                chosen_partial_denial,
                enclosure_before,
            )
            best_value_axis, best_candidate, best_breakdown = self._best_analysis_candidate(
                game, board, player, opponent, reachable_before, enclosure_before, pool
            )

            note = self._analysis_note(
                game, chosen_total, chosen_breakdown, best_value_axis, best_candidate, best_breakdown
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

            suffixes = []
            if game.prize_enabled and s["prizes"]:
                suffixes.append(f"Prize {s['prizes']}")
            if s["potential_area"]:
                suffixes.append(f"+{s['potential_area']} area")
            if game.prize_enabled and s["potential_prize_points"]:
                suffixes.append(f"+{s['potential_prize_points']} prize")
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
