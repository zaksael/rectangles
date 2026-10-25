package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Player
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnRecord

/**
 * What one candidate does on each axis, in cells: special cells covered, cells taken from the
 * opponent's reach, and the change in the mover's own enclosed cells.
 */
final case class AxisBreakdown(
    prizeCells: Int,
    pitfallCells: Int,
    stealCells: Int,
    denialCells: Int,
    enclosureDelta: Int,
)

/** The axis a flagged turn lost most on. */
enum AnalysisAxis:
  case Prize, Pitfall, Steal, Denial, Enclosure

/**
 * `chosen` and `best` are cells denied for `Denial` and real points for the rest; `better` is the
 * candidate that ranked higher than the move played.
 */
final case class TurnAnalysis(axis: AnalysisAxis, chosen: Int, best: Int, better: Candidate)

object Analysis:
  /**
   * One flag per turn (keyed by 1-based move number, clean turns absent) where another legal
   * candidate would have ranked higher than the move played. Skips are never flagged, and a forced
   * move cannot be (the pool holds only the chosen candidate). One incremental walk over history.
   */
  def turnAnalyses(state: GameState): Map[Int, TurnAnalysis] =
    val walk = state.history.zipWithIndex.foldLeft((
      Scoring.emptyCopy(state),
      Map.empty[Int, TurnAnalysis],
    )) {
      case ((scratch, found), (record, index)) =>
        record.placed.fold((scratch, found)) { placed =>
          val chosen = Candidate(placed.topLeft, placed.width, placed.height)
          val flag   = analyse(scratch, record, chosen)
          val result =
            Placement.place(
              scratch.board,
              scratch.players(record.playerId),
              chosen.topLeft,
              chosen.width,
              chosen.height,
            )
          (
            scratch.copy(
              board = result.board,
              players = scratch.players.updated(record.playerId, result.player),
            ),
            found ++ flag.map((index + 1) -> _),
          )
        }
    }
    walk._2

  /** The flag for one move, if a candidate in its pool ranked higher than the move played. */
  private def analyse(
      scratch: GameState,
      record: TurnRecord,
      chosen: Candidate,
  ): Option[TurnAnalysis] =
    val rules           = scratch.rules
    val board           = scratch.board
    val player          = scratch.players(record.playerId)
    val opponent        = scratch.players(record.playerId.other)
    val reachableBefore = board.reachableEmptyCells(opponent).size
    val enclosureBefore =
      if rules.selfEnclosedPenalty then board.selfEnclosedCellCounts.getOrElse(player.id, 0) else 0
    val chosenAxes =
      fullAxes(rules, board, player, opponent, chosen, reachableBefore, enclosureBefore)
    bestCandidate(
      rules,
      board,
      player,
      opponent,
      reachableBefore,
      enclosureBefore,
      candidatePool(record, board, player),
    ).filter((value, _, _) => value > rankingValue(chosenAxes)).map((_, better, bestAxes) =>
      describe(rules, chosenAxes, bestAxes, better)
    )

  /**
   * The highest-ranked candidate, the first in pool order on a tie. A candidate's enclosure bonus
   * can never exceed `enclosureBefore`, so the flood fill is skipped for any whose cheap value plus
   * that ceiling cannot beat the running best (exact: a skipped candidate could never have won).
   * shortcut: the ceiling is player-wide, not scoped to the regions a candidate touches, so it
   * prunes little once a player has several self-enclosed cells; upgrade to a region-scoped bound
   * if a deep 27x27 game with wildcard and enclosure is ever felt to be slow.
   */
  private def bestCandidate(
      rules: Rules,
      board: Board,
      player: Player,
      opponent: Player,
      reachableBefore: Int,
      enclosureBefore: Int,
      pool: Vector[Candidate],
  ): Option[(Int, Candidate, AxisBreakdown)] =
    val ceiling =
      if rules.selfEnclosedPenalty then enclosureBefore * Constants.SELF_ENCLOSED_PENALTY_PER_CELL
      else 0
    pool.foldLeft(Option.empty[(Int, Candidate, AxisBreakdown)]) { (best, candidate) =>
      val partial = partialAxes(rules, board, player, opponent, candidate, reachableBefore)
      if best.exists(_._1 >= rankingValue(partial) + ceiling) then best
      else
        val axes  = withEnclosure(rules, board, player, candidate, partial, enclosureBefore)
        val value = rankingValue(axes)
        if best.forall(value > _._1) then Some((value, candidate, axes)) else best
    }

  /**
   * The largest weighted gap names the axis (ties: Prize, Pitfall, Steal, Denial, Enclosure), and
   * the numbers are the right kind for it: cells denied for denial, real points otherwise. The
   * ranking value blends the two and is never reported.
   */
  private def describe(
      rules: Rules,
      chosen: AxisBreakdown,
      best: AxisBreakdown,
      better: Candidate,
  ): TurnAnalysis =
    def gap(enabled: Boolean, value: Int) = if enabled then value else 0
    val gaps = List(
      gap(rules.prize, (best.prizeCells - chosen.prizeCells) * pointsOf(CellKind.Prize))
        -> AnalysisAxis.Prize,
      gap(rules.pitfall, (chosen.pitfallCells - best.pitfallCells) * pointsOf(CellKind.Pitfall))
        -> AnalysisAxis.Pitfall,
      gap(rules.steal, (best.stealCells - chosen.stealCells) * 2 * pointsOf(CellKind.Steal))
        -> AnalysisAxis.Steal,
      (best.denialCells - chosen.denialCells) -> AnalysisAxis.Denial,
      gap(
        rules.selfEnclosedPenalty,
        (chosen.enclosureDelta - best.enclosureDelta) * Constants.SELF_ENCLOSED_PENALTY_PER_CELL,
      ) -> AnalysisAxis.Enclosure,
    )
    gaps.maxBy(_._1)._2 match
      case AnalysisAxis.Denial =>
        TurnAnalysis(AnalysisAxis.Denial, chosen.denialCells, best.denialCells, better)
      case axis => TurnAnalysis(axis, points(chosen), points(best), better)

  /**
   * The cheap axes for one candidate: Prize, Pitfall and Steal are exact cell-overlap counts;
   * denial is the opponent's reach lost, with no cheap bound, so it is always paid. Enclosure is
   * left at 0 (it needs a flood fill, which the caller can skip for candidates that cannot win).
   */
  def partialAxes(
      rules: Rules,
      board: Board,
      player: Player,
      opponent: Player,
      candidate: Candidate,
      reachableBefore: Int,
  ): AxisBreakdown =
    def covered(enabled: Boolean, kind: CellKind) =
      if enabled then Bot.cellOverlapScore(candidate, board.cellsOfKind(kind)) else 0
    val after = placeOn(board, player, candidate)
    AxisBreakdown(
      prizeCells = covered(rules.prize, CellKind.Prize),
      pitfallCells = covered(rules.pitfall, CellKind.Pitfall),
      stealCells = covered(rules.steal, CellKind.Steal),
      denialCells = reachableBefore - after.reachableEmptyCells(opponent).size,
      enclosureDelta = 0,
    )

  def fullAxes(
      rules: Rules,
      board: Board,
      player: Player,
      opponent: Player,
      candidate: Candidate,
      reachableBefore: Int,
      enclosureBefore: Int,
  ): AxisBreakdown =
    withEnclosure(
      rules,
      board,
      player,
      candidate,
      partialAxes(rules, board, player, opponent, candidate, reachableBefore),
      enclosureBefore,
    )

  /**
   * One turn-quality value on the weights the score uses, so candidates rank on one scale. A Steal
   * counts twice (it swings both totals, as in `Bot.specialCellScore`). Denial carries weight 1: a
   * ranking value only, never shown as score.
   */
  def rankingValue(axes: AxisBreakdown): Int =
    points(axes) + axes.stealCells * pointsOf(CellKind.Steal) + axes.denialCells

  private def pointsOf(kind: CellKind): Int = Constants.SPECIAL_CELL_KINDS(kind).points

  private def points(axes: AxisBreakdown): Int =
    axes.prizeCells * pointsOf(CellKind.Prize) - axes.pitfallCells * pointsOf(CellKind.Pitfall) +
      axes.stealCells * pointsOf(CellKind.Steal) -
      axes.enclosureDelta * Constants.SELF_ENCLOSED_PENALTY_PER_CELL

  /** The board with the candidate placed for `player`; the what-if every axis is measured on. */
  private def placeOn(board: Board, player: Player, candidate: Candidate): Board =
    Placement.place(board, player, candidate.topLeft, candidate.width, candidate.height).board

  private def withEnclosure(
      rules: Rules,
      board: Board,
      player: Player,
      candidate: Candidate,
      axes: AxisBreakdown,
      enclosureBefore: Int,
  ): AxisBreakdown =
    if !rules.selfEnclosedPenalty then axes
    else
      val after = placeOn(board, player, candidate).selfEnclosedCellCounts.getOrElse(player.id, 0)
      axes.copy(enclosureDelta = after - enclosureBefore)

  /**
   * Every placement this turn could have used: the rolled orientation pair, or every wildcard
   * value's orientations on a wildcard turn. Top-lefts run row by row, so a tie on value always
   * resolves to the same candidate.
   */
  def candidatePool(record: TurnRecord, board: Board, player: Player): Vector[Candidate] =
    val sizes = record.wildcardOriginalRoll.fold(
      Vector((record.roll.first, record.roll.second), (record.roll.second, record.roll.first))
    ) { original =>
      for
        value  <- (Constants.DICE_MIN to Constants.DICE_MAX).toVector
        (w, h) <- Vector((original.first, value), (value, original.first))
      yield (w, h)
    }
    for
      (width, height) <- sizes.distinct
      topLeft <- Placement
        .legalTopLefts(board, player, width, height)
        .toVector
        .sortBy(cell => (cell.row, cell.col))
    yield Candidate(topLeft, width, height)
