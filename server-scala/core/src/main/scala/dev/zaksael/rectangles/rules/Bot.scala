package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.TurnState

/** A placement the bot can pick: where the piece's top-left cell goes and how big it is. */
final case class Candidate(topLeft: Cell, width: Int, height: Int):
  def cells: Set[Cell] =
    (for
      row <- topLeft.row until topLeft.row + height
      col <- topLeft.col until topLeft.col + width
    yield Cell(row, col)).toSet

object Bot:
  /**
   * Every spot in `legal`, in (row, col, width, height) order so a draw index means the same thing.
   */
  private def candidates(legal: Map[Roll, Set[Cell]]): Vector[Candidate] =
    legal.toVector
      .flatMap((roll, cells) => cells.map(Candidate(_, roll.first, roll.second)))
      .sortBy(c => (c.topLeft.row, c.topLeft.col, c.width, c.height))

  def cellOverlapScore(candidate: Candidate, cells: Set[Cell]): Int =
    candidate.cells.count(cells)

  /** Prize gained, Pitfall avoided, Steal at double weight: it swings the gap both ways at once. */
  def specialCellScore(candidate: Candidate, board: Board): Int =
    def covered(kind: CellKind) = cellOverlapScore(candidate, board.cellsOfKind(kind))
    def points(kind: CellKind)  = Constants.SPECIAL_CELL_KINDS(kind).points
    covered(CellKind.Prize) * points(CellKind.Prize) +
      covered(CellKind.Steal) * 2 * points(CellKind.Steal) -
      covered(CellKind.Pitfall) * points(CellKind.Pitfall)

  def blockingScore(candidate: Candidate, opponentFrontier: Set[Cell]): Int =
    cellOverlapScore(candidate, opponentFrontier)

  /** The frontier is taken once here, not per candidate: it scans the whole board. */
  private def blockingFn(state: GameState): Candidate => Int =
    val frontier = state.board.frontier(state.current.other)
    c => blockingScore(c, frontier) + specialCellScore(c, state.board)

  /** The best-scoring item; a tie is broken by one draw among the best, a clear winner by none. */
  private def breakTie[K: Ordering, A](scored: Vector[(K, A)], dice: Dice): (A, Dice) =
    val best = scored.map(_._1).max
    scored.collect { case (key, item) if key == best => item } match
      case Vector(only) => (only, dice)
      case tied         => dice.choose(tied)

  /** How each smart difficulty scores a candidate; Basic has no score. */
  private def scoreFn(state: GameState, difficulty: BotDifficulty): Option[Candidate => Int] =
    difficulty match
      case BotDifficulty.Basic    => None
      case BotDifficulty.Greedy   => Some(specialCellScore(_, state.board))
      case BotDifficulty.Blocking => Some(blockingFn(state))

  private def bestScore(spots: Vector[Candidate], score: Candidate => Int): Int =
    spots.map(score).maxOption.getOrElse(0)

  /** Needs a legal value to pick from, which the wildcard-choosing turn state guarantees. */
  def chooseWildcardValue(
      state: GameState,
      difficulty: BotDifficulty,
      dice: Dice,
  ): (Int, Dice) =
    scoreFn(state, difficulty) match
      // Basic draws any value, legal or not: an illegal one costs it the turn.
      case None => dice.between(Constants.DICE_MIN, Constants.DICE_MAX)
      case Some(score) =>
        val scored = Turns.legalValues(state).map { value =>
          val spots = Turns.legalPlacementsForValue(state, value)
          // Unlike placements within one roll, values differ in piece size: Greedy's ties go to the larger.
          val area =
            if difficulty == BotDifficulty.Greedy then
              spots.collect { case (roll, cells) if cells.nonEmpty => roll.first * roll.second }
                .maxOption
                .getOrElse(0)
            else 0
          ((bestScore(candidates(spots), score), area), value)
        }
        require(scored.nonEmpty, "no legal wildcard value")
        breakTie(scored, dice)

  /** The cells whose capture would lift this difficulty's score above zero. */
  private def gainableCells(state: GameState, difficulty: BotDifficulty): Set[Cell] =
    val gains = state.board.cellsOfKind(CellKind.Prize) ++ state.board.cellsOfKind(CellKind.Steal)
    if difficulty == BotDifficulty.Blocking then gains ++ state.board.frontier(state.current.other)
    else gains

  /**
   * Whether some roll could still cover a gainable cell. A piece is at most DICE_MAX wide and must
   * start touching the mover's territory (or start corner), so only cells within DICE_MAX - 1 of an
   * anchor count. Over-counts (ignores legality) but never misses a reachable cell.
   */
  private def gainInReach(state: GameState, difficulty: BotDifficulty): Boolean =
    val player  = state.players(state.current)
    val front   = state.board.frontier(player.id)
    val anchors = if front.isEmpty then Set(player.startCorner) else front
    val reach   = Constants.DICE_MAX - 1
    gainableCells(state, difficulty).exists(gain =>
      anchors.exists(a => math.max(math.abs(gain.row - a.row), math.abs(gain.col - a.col)) <= reach)
    )

  def shouldReroll(state: GameState, difficulty: BotDifficulty): Boolean =
    scoreFn(state, difficulty) match
      case Some(score) if Rerolls.canReroll(state) =>
        // A forced loss (a Pitfall) is worth a charge; a zero only when some roll could still score.
        def worth(best: Int) = best < 0 || (best == 0 && gainInReach(state, difficulty))
        state.turn match
          case TurnState.Skipped => true
          case TurnState.ChoosingPlacement =>
            worth(bestScore(candidates(state.legal), score))
          case TurnState.ChoosingWildcard =>
            Turns.legalValues(state)
              .map(v => bestScore(candidates(Turns.legalPlacementsForValue(state, v)), score))
              .maxOption
              .exists(worth)
          case _ => false
      case _ => false

  /** Needs at least one legal placement, which the placement-choosing turn state guarantees. */
  def choosePlacement(
      state: GameState,
      difficulty: BotDifficulty,
      dice: Dice,
  ): (Candidate, Dice) =
    val all = candidates(state.legal)
    require(all.nonEmpty, "no legal placement")
    difficulty match
      case BotDifficulty.Greedy =>
        // Special cells tie at 0 when none is reachable; denial then decides instead of a bare draw.
        val blocking = blockingFn(state)
        breakTie(all.map(c => ((specialCellScore(c, state.board), blocking(c)), c)), dice)
      case BotDifficulty.Blocking =>
        val score = blockingFn(state)
        breakTie(all.map(c => (score(c), c)), dice)
      case BotDifficulty.Basic => dice.choose(all)
