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
  def breakdown(state: GameState, who: PlayerId): ScoreBreakdown =
    ScoreBreakdown(area = state.players(who).totalArea)

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

  /** The game rebuilt from an empty board, once per history record, after that record. */
  private def replay(state: GameState): Vector[GameState] =
    val empty = state.copy(
      board = state.board.copy(owners = Map.empty),
      players = state.players.view.mapValues(p => Player(p.id, p.name, p.startCorner)).toMap,
    )
    state.history
      .scanLeft(empty) { (step, record) =>
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
