package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Player
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.ScoreBreakdown

/** What a player could still end up with: the empty cells they can reach. */
final case class Potential(area: Int, prizePoints: Int)

object Scoring:
  /** Empty cells only `who` encloses; always 0 with the penalty rule off. */
  def selfEnclosedCells(state: GameState, who: PlayerId): Int =
    if state.rules.selfEnclosedPenalty then state.board.selfEnclosedCellCounts.getOrElse(who, 0)
    else 0

  def breakdown(state: GameState, who: PlayerId): ScoreBreakdown =
    val mine   = state.players(who)
    val theirs = state.players(who.other)
    val points = Constants.SPECIAL_CELL_KINDS.map { (kind, effect) =>
      kind -> (effect.capturerSign * mine.specialCaptures.getOrElse(kind, 0) +
        effect.opponentSign * theirs.specialCaptures.getOrElse(kind, 0)) * effect.points
    }
    ScoreBreakdown(
      area = mine.totalArea,
      prize = points(CellKind.Prize),
      pitfall = points(CellKind.Pitfall),
      steal = points(CellKind.Steal),
      enclosure = -selfEnclosedCells(state, who) * Constants.SELF_ENCLOSED_PENALTY_PER_CELL,
    )

  def total(state: GameState, who: PlayerId): Int = breakdown(state, who).total

  def winner(state: GameState): Option[PlayerId] = state.gameOver match
    case Some(GameOverReason.Surrendered(who)) => Some(who.other)
    case _ =>
      val one = total(state, PlayerId.One)
      val two = total(state, PlayerId.Two)
      if one > two then Some(PlayerId.One) else if two > one then Some(PlayerId.Two) else None

  def breakdownHistory(state: GameState): Vector[Map[PlayerId, ScoreBreakdown]] =
    replay(state).map(step => step.players.keys.map(who => who -> breakdown(step, who)).toMap)

  def potential(board: Board, player: Player): Potential =
    val reachable = board.reachableEmptyCells(player)
    Potential(
      reachable.size,
      (reachable & board.cellsOfKind(CellKind.Prize)).size * Constants.PRIZE_BONUS_POINTS,
    )

  def potentialHistory(state: GameState): Vector[Map[PlayerId, Potential]] =
    replay(state).map(step => step.players.view.mapValues(potential(step.board, _)).toMap)

  /**
   * The same board geometry with nothing placed, and the players unplayed at their start corners.
   */
  private[rules] def emptyCopy(state: GameState): GameState =
    state.copy(
      board = state.board.copy(owners = Map.empty),
      players = state.players.view.mapValues(p => Player(p.id, p.name, p.startCorner)).toMap,
    )

  /** The game rebuilt from an empty board, once per history record, after that record. */
  private def replay(state: GameState): Vector[GameState] =
    state.history
      .scanLeft(emptyCopy(state)) { (step, record) =>
        record.placed.fold(step) { rect =>
          val result =
            Placement.place(
              step.board,
              step.players(record.playerId),
              rect.topLeft,
              rect.width,
              rect.height,
            )
          step.copy(
            board = result.board,
            players = step.players.updated(record.playerId, result.player),
          )
        }
      }
      .drop(1)
