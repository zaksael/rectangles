package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PendingWildcard
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.domain.TurnState

enum RuleError:
  case WrongState, IllegalPlacement, IllegalWildcardValue

object Turns:
  def rollDice(state: GameState, dice: Dice): Either[RuleError, (GameState, Dice)] =
    if state.turn != TurnState.AwaitingRoll then Left(RuleError.WrongState)
    else
      val (first, afterFirst)   = dice.between(Constants.DICE_MIN, Constants.DICE_MAX)
      val (second, afterSecond) = afterFirst.between(Constants.DICE_MIN, Constants.DICE_MAX)
      val roll                  = Roll(first, second)
      if state.rules.wildcard && first == second then
        val (index, afterIndex) = afterSecond.between(0, 1)
        val pending             = PendingWildcard(Some(index), roll)
        val picking = state.copy(
          lastRoll = Some(roll),
          legal = Map.empty,
          turn = TurnState.ChoosingWildcard,
          wildcard = Some(pending),
        )
        val anyFits = legalValues(picking).nonEmpty
        // A picker where no value fits would only lead to the skip, so go straight to it.
        val resolved =
          if anyFits then picking
          else resolve(picking.copy(wildcard = Some(pending.copy(editableIndex = None))), roll)
        Right((resolved, afterIndex))
      else Right((resolve(state, roll), afterSecond))

  /** Both orientations of `roll` with the spots where each could go. */
  private def legalFor(state: GameState, roll: Roll): Map[Roll, Set[Cell]] =
    val player  = state.players(state.current)
    val flipped = Roll(roll.second, roll.first)
    Map(
      roll    -> Placement.legalTopLefts(state.board, player, roll.first, roll.second),
      flipped -> Placement.legalTopLefts(state.board, player, flipped.first, flipped.second),
    )

  /**
   * Settles a roll: a placement to choose, or a skip (recorded unless a reroll could discard it).
   */
  private def resolve(state: GameState, roll: Roll): GameState =
    val legal = legalFor(state, roll)
    val turn =
      if legal.values.exists(_.nonEmpty) then TurnState.ChoosingPlacement else TurnState.Skipped
    val rolled = state.copy(lastRoll = Some(roll), legal = legal, turn = turn)
    if turn == TurnState.Skipped && !Rerolls.canReroll(rolled) then commitSkip(rolled, roll)
    else rolled

  /** Records the current player's skipped turn. */
  private def commitSkip(state: GameState, roll: Roll): GameState =
    val player = state.players(state.current)
    state.copy(
      players = state.players.updated(
        state.current,
        player.copy(consecutiveSkips = player.consecutiveSkips + 1),
      ),
      history = state.history :+
        TurnRecord(state.current, roll, None, state.wildcard.map(_.originalRoll)),
    )

  /** Discards the roll for a fresh one, spending a charge; allowed while a roll is pending. */
  def reroll(state: GameState, dice: Dice): Either[RuleError, (GameState, Dice)] =
    val pending = Set(TurnState.ChoosingWildcard, TurnState.ChoosingPlacement, TurnState.Skipped)
    if !pending(state.turn) || !Rerolls.canReroll(state) then Left(RuleError.WrongState)
    else
      val player = state.players(state.current)
      rollDice(
        state.copy(
          players =
            state.players.updated(state.current, player.copy(rerollsUsed = player.rerollsUsed + 1)),
          lastRoll = None,
          legal = Map.empty,
          turn = TurnState.AwaitingRoll,
          wildcard = None,
        ),
        dice,
      )

  /** Sets the wildcard die to `value` and settles the roll that results. */
  def chooseWildcard(state: GameState, value: Int): Either[RuleError, GameState] =
    if state.turn != TurnState.ChoosingWildcard then Left(RuleError.WrongState)
    else if value < Constants.DICE_MIN || value > Constants.DICE_MAX then
      Left(RuleError.IllegalWildcardValue)
    else
      state.lastRoll.zip(state.wildcard).headOption match
        case Some((roll, pending)) =>
          val chosen =
            if pending.editableIndex.contains(0) then Roll(value, roll.second)
            else Roll(roll.first, value)
          Right(resolve(state.copy(wildcard = Some(pending.copy(editableIndex = None))), chosen))
        case None => Left(RuleError.WrongState)

  /** The die values that would leave a placement while the wildcard picker is open. */
  def legalValues(state: GameState): Vector[Int] =
    (Constants.DICE_MIN to Constants.DICE_MAX).filter { value =>
      legalPlacementsForValue(state, value).values.exists(_.nonEmpty)
    }.toVector

  /** The spots for the roll if the wildcard die became `value`; empty outside the picker. */
  def legalPlacementsForValue(state: GameState, value: Int): Map[Roll, Set[Cell]] =
    state.lastRoll.zip(state.wildcard.flatMap(_.editableIndex)).headOption.fold(Map.empty) {
      (roll, index) =>
        legalFor(state, if index == 0 then Roll(value, roll.second) else Roll(roll.first, value))
    }

  def attemptPlace(
      state: GameState,
      topLeft: Cell,
      width: Int,
      height: Int,
  ): Either[RuleError, GameState] =
    state.lastRoll.filter(_ =>
      state.legal.get(Roll(width, height)).exists(_.contains(topLeft))
    ) match
      case _ if state.turn == TurnState.GameOver => Left(RuleError.WrongState)
      case None                                  => Left(RuleError.IllegalPlacement)
      case Some(rolled) =>
        val result =
          Placement.place(state.board, state.players(state.current), topLeft, width, height)
        val record =
          TurnRecord(
            state.current,
            rolled,
            Some(result.rectangle),
            state.wildcard.map(_.originalRoll),
          )
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
        wildcard = None,
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

  /** Acknowledges a skipped turn; a skip held back for a reroll is recorded now, once. */
  def confirmSkip(state: GameState): Either[RuleError, GameState] =
    if state.turn != TurnState.Skipped then Left(RuleError.WrongState)
    else
      Right(
        if Rerolls.canReroll(state) && !recorded(state) then
          state.lastRoll.fold(state)(commitSkip(state, _))
        else state
      )

  /** Whether the latest history record is this player's skip of the pending roll. */
  private def recorded(state: GameState): Boolean =
    state.history.lastOption.exists(record =>
      record.playerId == state.current && record.placed.isEmpty && state.lastRoll.contains(
        record.roll
      )
    )
