from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from . import bot, constants
from .board import Board
from .constants import CellKind
from .game import Game
from .models import Player, TurnRecord


@dataclass(frozen=True)
class Candidate:
    top_left: tuple[int, int]
    width: int
    height: int


@dataclass(frozen=True)
class AxisBreakdown:
    prize_cells: int
    pitfall_cells: int
    denial_cells: int
    enclosure_delta: int


def candidate_pool(record: TurnRecord, board: Board, player: Player) -> list[Candidate]:
    """Every placement this turn could have used: the rolled orientation pair, or every
    wildcard value's orientations on a Wildcard Roll turn."""
    a, b = record.roll
    if record.wildcard_original_roll is not None:
        fixed = record.wildcard_original_roll[0]
        sizes = [
            size
            for value in range(constants.DICE_MIN, constants.DICE_MAX + 1)
            for size in ((fixed, value), (value, fixed))
        ]
    else:
        sizes = [(a, b), (b, a)]
    return [Candidate(top_left, w, h) for w, h in sizes for top_left in board.legal_top_lefts(player, w, h)]


def partial_axes(
    game: Game, board: Board, player: Player, opponent: Player, candidate: Candidate, reachable_before: int
) -> AxisBreakdown:
    """The cheap axes for one candidate: prize and pitfall are exact cell-overlap counts; denial is a
    reachable-area cutoff with no cheap bound, so it is always paid. Enclosure is left at 0 (it needs
    a flood-fill, which the caller can skip for candidates that cannot win)."""
    cell = (candidate.top_left, candidate.width, candidate.height)
    prize_cells = bot.cell_overlap_score(cell, board.cells_of_kind(CellKind.PRIZE)) if game.prize_enabled else 0
    pitfall_cells = (
        bot.cell_overlap_score(cell, board.cells_of_kind(CellKind.PITFALL)) if game.pitfall_enabled else 0
    )
    denial_cells = reachable_before - board.reachable_count_if(
        player.id, opponent, candidate.top_left, candidate.width, candidate.height
    )
    return AxisBreakdown(prize_cells, pitfall_cells, denial_cells, 0)


def ranking_value(game: Game, axes: AxisBreakdown) -> int:
    """One turn-quality value on the weights Game.total_score() uses, so candidates rank on one scale.
    Denial carries weight 1 (no total_score() equivalent): a ranking value only, never shown as score."""
    return _points(game, axes) + axes.denial_cells


class AnalysisAxis(Enum):
    PRIZE = "prize"
    PITFALL = "pitfall"
    DENIAL = "denial"
    ENCLOSURE = "enclosure"


@dataclass(frozen=True)
class TurnAnalysis:
    axis: AnalysisAxis
    chosen: int
    best: int
    better: Candidate


def full_axes(
    game: Game,
    board: Board,
    player: Player,
    opponent: Player,
    candidate: Candidate,
    reachable_before: int,
    enclosure_before: int,
) -> AxisBreakdown:
    axes = partial_axes(game, board, player, opponent, candidate, reachable_before)
    return _with_enclosure(game, board, player, candidate, axes, enclosure_before)


def _with_enclosure(
    game: Game, board: Board, player: Player, candidate: Candidate, axes: AxisBreakdown, enclosure_before: int
) -> AxisBreakdown:
    if not game.self_enclosed_penalty_enabled:
        return axes
    after = board.self_enclosed_count_if(player.id, candidate.top_left, candidate.width, candidate.height)
    return replace(axes, enclosure_delta=after - enclosure_before)


def _best_candidate(
    game: Game,
    board: Board,
    player: Player,
    opponent: Player,
    reachable_before: int,
    enclosure_before: int,
    pool: list[Candidate],
) -> tuple[int, Candidate, AxisBreakdown]:
    # self_enclosed_count_if is an O(board_size^2) flood-fill and a Wildcard pool can be hundreds of
    # candidates. A candidate's enclosure bonus can never exceed enclosure_before, so skip the flood-fill
    # for any whose cheap value plus that ceiling cannot beat the running best (exact: a skipped
    # candidate could never have won).
    # shortcut: the ceiling is player-wide, not scoped to the regions a candidate touches, so it prunes
    # little once a player has several self-enclosed cells; deep 27x27 games with Wildcard and Enclosure
    # can still take ~1s. Upgrade to a region-scoped bound if that is ever felt.
    ceiling_bonus = enclosure_before * constants.SELF_ENCLOSED_PENALTY_PER_CELL if game.self_enclosed_penalty_enabled else 0
    best_value: int | None = None
    # pool always contains the chosen move, so the loop always sets these.
    for candidate in pool:
        partial = partial_axes(game, board, player, opponent, candidate, reachable_before)
        if best_value is not None and ranking_value(game, partial) + ceiling_bonus <= best_value:
            continue
        axes = _with_enclosure(game, board, player, candidate, partial, enclosure_before)
        value = ranking_value(game, axes)
        if best_value is None or value > best_value:
            best_value, best_candidate, best_axes = value, candidate, axes
    return best_value, best_candidate, best_axes  # type: ignore[return-value,possibly-undefined]


def _points(game: Game, axes: AxisBreakdown) -> int:
    return (
        axes.prize_cells * game.points_for(CellKind.PRIZE)
        - axes.pitfall_cells * game.points_for(CellKind.PITFALL)
        - axes.enclosure_delta * constants.SELF_ENCLOSED_PENALTY_PER_CELL
    )


def _analysis(
    game: Game, chosen: AxisBreakdown, best: AxisBreakdown, better: Candidate
) -> TurnAnalysis:
    # The largest weighted gap names the axis (ties: prize > pitfall > denial > enclosure), and the
    # numbers shown are the right kind for it: cells denied for denial, real points otherwise. The
    # ranking value itself blends the two and is never reported.
    gaps = (
        (
            (best.prize_cells - chosen.prize_cells) * game.points_for(CellKind.PRIZE) if game.prize_enabled else 0,
            AnalysisAxis.PRIZE,
        ),
        (
            (chosen.pitfall_cells - best.pitfall_cells) * game.points_for(CellKind.PITFALL)
            if game.pitfall_enabled
            else 0,
            AnalysisAxis.PITFALL,
        ),
        (best.denial_cells - chosen.denial_cells, AnalysisAxis.DENIAL),
        (
            (chosen.enclosure_delta - best.enclosure_delta) * constants.SELF_ENCLOSED_PENALTY_PER_CELL
            if game.self_enclosed_penalty_enabled
            else 0,
            AnalysisAxis.ENCLOSURE,
        ),
    )
    _gap, axis = max(gaps, key=lambda gap_axis: gap_axis[0])
    if axis is AnalysisAxis.DENIAL:
        return TurnAnalysis(axis, chosen.denial_cells, best.denial_cells, better)
    return TurnAnalysis(axis, _points(game, chosen), _points(game, best), better)


def turn_analyses(game: Game) -> dict[int, TurnAnalysis]:
    """One flag per turn (keyed by 1-based move number, clean turns absent) where another legal
    candidate would have ranked higher than the move played. Skips are never flagged, and a forced
    move cannot be (the pool holds only the chosen candidate). One incremental walk over history."""
    board, scratch = game.new_scratch()
    analyses: dict[int, TurnAnalysis] = {}
    for step, record in enumerate(game.history, start=1):
        if record.placed is None:
            continue
        player = scratch[record.player_id]
        opponent = scratch[constants.PLAYER_2 if record.player_id == constants.PLAYER_1 else constants.PLAYER_1]
        reachable_before = len(board.reachable_empty_cells(opponent))
        enclosure_before = (
            board.self_enclosed_cell_counts().get(player.id, 0) if game.self_enclosed_penalty_enabled else 0
        )
        placed = record.placed
        chosen_candidate = Candidate(placed.top_left, placed.width, placed.height)
        chosen = full_axes(game, board, player, opponent, chosen_candidate, reachable_before, enclosure_before)
        pool = candidate_pool(record, board, player)
        best_value, best_candidate, best = _best_candidate(
            game, board, player, opponent, reachable_before, enclosure_before, pool
        )
        if best_value > ranking_value(game, chosen):
            analyses[step] = _analysis(game, chosen, best, best_candidate)
        board.place(player, placed.top_left, placed.width, placed.height)
    return analyses
