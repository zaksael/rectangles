package dev.zaksael.rectangles.server.session

import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.RuleError
import dev.zaksael.rectangles.rules.Turns
import dev.zaksael.rectangles.server.protocol.ClientMessage
import dev.zaksael.rectangles.server.protocol.ErrorMsg
import dev.zaksael.rectangles.server.protocol.ErrorReason

/** The game and the dice its next roll comes from. */
final case class Play(state: GameState, dice: Dice)

object Actions:
  def apply(play: Play, message: ClientMessage): Either[ErrorMsg, Play] =
    message match
      case ClientMessage.Roll =>
        Turns.rollDice(play.state, play.dice).left.map(rejected).map(Play.apply.tupled)
      case ClientMessage.Place(topLeft, width, height) =>
        Turns
          .attemptPlace(play.state, topLeft, width, height)
          .left
          .map(rejected)
          .map(placed => play.copy(state = advance(placed)))
      case ClientMessage.Skip =>
        Turns.confirmSkip(play.state).left.map(rejected).map(skipped =>
          play.copy(state = advance(skipped))
        )
      case ClientMessage.Reroll =>
        Turns.reroll(play.state, play.dice).left.map(rejected).map(Play.apply.tupled)
      case ClientMessage.Surrender => Right(play.copy(state = Turns.surrender(play.state)))
      case _ =>
        Left(ErrorMsg(ErrorReason.InvalidAction, s"cannot apply $message to ${play.state.turn}"))

  /** After a placement or a skip: end the game if it is over, else pass the turn. */
  private def advance(state: GameState): GameState =
    val checked = Turns.checkGameOver(state)
    if checked.turn == TurnState.GameOver then checked else Turns.endTurn(checked)

  private def rejected(error: RuleError): ErrorMsg = error match
    case RuleError.WrongState =>
      ErrorMsg(ErrorReason.InvalidAction, "not allowed in this turn state")
    case RuleError.IllegalPlacement => ErrorMsg(ErrorReason.IllegalPlacement, "illegal placement")
    case RuleError.IllegalWildcardValue =>
      ErrorMsg(ErrorReason.IllegalWildcardValue, "wildcard value must be between 1 and 6")
