package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
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
      val resolved =
        if turn == TurnState.Skipped then
          rolled.copy(
            players = state.players.updated(
              state.current,
              player.copy(consecutiveSkips = player.consecutiveSkips + 1),
            ),
            history = rolled.history :+ TurnRecord(state.current, roll, None),
          )
        else rolled
      Right((resolved, afterSecond))

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
          state.copy(
            board = result.board,
            players = state.players.updated(state.current, result.player),
            history = state.history :+ record,
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
