package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.domain.TurnState

enum RuleError:
  case WrongState, IllegalPlacement

object Turns:
  def rollDice(state: GameState, dice: Dice): Either[RuleError, (GameState, Dice)] =
    if state.turn != TurnState.AwaitingRoll then Left(RuleError.WrongState)
    else
      val (first, afterFirst)   = dice.between(Constants.DICE_MIN, Constants.DICE_MAX)
      val (second, afterSecond) = afterFirst.between(Constants.DICE_MIN, Constants.DICE_MAX)
      val roll                  = Roll(first, second)
      val player                = state.players(state.current)
      val legal = Map(
        roll                -> Placement.legalTopLefts(state.board, player, first, second),
        Roll(second, first) -> Placement.legalTopLefts(state.board, player, second, first),
      )
      val turn =
        if legal.values.exists(_.nonEmpty) then TurnState.ChoosingPlacement else TurnState.Skipped
      val rolled = state.copy(lastRoll = Some(roll), legal = legal, turn = turn)
      // A skip waits to be recorded while a reroll charge could still discard it.
      val resolved =
        if turn == TurnState.Skipped && !Rerolls.canReroll(rolled) then commitSkip(rolled, roll)
        else rolled
      Right((resolved, afterSecond))

  /** Records the current player's skipped turn. */
  private def commitSkip(state: GameState, roll: Roll): GameState =
    val player = state.players(state.current)
    state.copy(
      players =
        state.players.updated(
          state.current,
          player.copy(consecutiveSkips = player.consecutiveSkips + 1),
        ),
      history =
        state.history :+ TurnRecord(state.current, roll, None),
    )

  /** Discards the roll for a fresh one, spending a charge; allowed while a roll is pending. */
  def reroll(state: GameState, dice: Dice): Either[RuleError, (GameState, Dice)] =
    val pending = state.turn == TurnState.ChoosingPlacement || state.turn == TurnState.Skipped
    if !pending || !Rerolls.canReroll(state) then Left(RuleError.WrongState)
    else
      val player = state.players(state.current)
      rollDice(
        state.copy(
          players =
            state.players.updated(state.current, player.copy(rerollsUsed = player.rerollsUsed + 1)),
          lastRoll = None,
          legal = Map.empty,
          turn = TurnState.AwaitingRoll,
        ),
        dice,
      )

  def attemptPlace(
      state: GameState,
      topLeft: Cell,
      width: Int,
      height: Int,
  ): Either[RuleError, GameState] =
    state.lastRoll.filter(_ =>
      state.legal.get(Roll(width, height)).exists(_.contains(topLeft))
    ) match
      case None => Left(RuleError.IllegalPlacement)
      case Some(rolled) =>
        val result =
          Placement.place(state.board, state.players(state.current), topLeft, width, height)
        val record = TurnRecord(state.current, rolled, Some(result.rectangle))
        Right(
          Rerolls.maybeGrantNudge(
            state.copy(
              board = result.board,
              players =
                state.players.updated(state.current, result.player.copy(consecutiveSkips = 0)),
              history = state.history :+ record,
            )
          )
        )

  def endTurn(state: GameState): GameState =
    if state.turn == TurnState.GameOver then state
    else
      state.copy(
        current = state.current.other,
        lastRoll = None,
        legal = Map.empty,
        turn = TurnState.AwaitingRoll,
      )

  /** Ends the game when the board is full, a player is boxed in or the skip limit is reached. */
  def checkGameOver(state: GameState): GameState =
    val noFrontier = PlayerId.values.filter(who => state.board.frontier(who).isEmpty)
    if noFrontier.length == PlayerId.values.length then ended(state, GameOverReason.BoardFull)
    else
      noFrontier.find(who => state.players(who).hasMoved) match
        case Some(who) => ended(state, GameOverReason.PlayerBlocked(who))
        case None =>
          PlayerId.values
            .find(who => state.players(who).consecutiveSkips >= state.rules.skipLimit)
            .fold(state)(who => ended(state, GameOverReason.SkipLimit(who)))

  private def ended(state: GameState, reason: GameOverReason): GameState =
    state.copy(turn = TurnState.GameOver, gameOver = Some(reason))

  def surrender(state: GameState): GameState =
    if state.turn == TurnState.GameOver then state
    else ended(state, GameOverReason.Surrendered(state.current))

  /** Acknowledges a skipped turn; a skip held back for a reroll is recorded now. */
  def confirmSkip(state: GameState): Either[RuleError, GameState] =
    if state.turn != TurnState.Skipped then Left(RuleError.WrongState)
    else
      Right(if Rerolls.canReroll(state) then state.lastRoll.fold(state)(commitSkip(state, _))
      else state)
