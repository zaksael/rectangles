package dev.zaksael.rectangles.server.session

import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.RuleError
import dev.zaksael.rectangles.rules.Series
import dev.zaksael.rectangles.rules.Turns
import dev.zaksael.rectangles.server.protocol.ClientMessage
import dev.zaksael.rectangles.server.protocol.ErrorMsg
import dev.zaksael.rectangles.server.protocol.ErrorReason

/** The game, the dice its next roll comes from, and the series it is a round of, if any. */
final case class Play(state: GameState, dice: Dice, series: Option[Series] = None):
  /**
   * This play after a step: `next` is the game, `nextDice` the dice left. The step that ends the
   * game adds its round to the series, so the state it is sent in already shows it.
   */
  def stepped(next: GameState, nextDice: Dice): Play =
    val ended = state.turn != TurnState.GameOver && next.turn == TurnState.GameOver
    Play(next, nextDice, if ended then series.map(_.record(next)) else series)

object Actions:
  def apply(play: Play, message: ClientMessage): Either[ErrorMsg, Play] =
    message match
      case ClientMessage.Roll =>
        Turns.rollDice(play.state, play.dice).left.map(rejected).map(play.stepped.tupled)
      case ClientMessage.Place(topLeft, width, height) =>
        Turns
          .attemptPlace(play.state, topLeft, width, height)
          .left
          .map(rejected)
          .map(placed => play.stepped(advance(placed), play.dice))
      case ClientMessage.Skip =>
        Turns.confirmSkip(play.state).left.map(rejected).map(skipped =>
          play.stepped(advance(skipped), play.dice)
        )
      case ClientMessage.Reroll =>
        Turns.reroll(play.state, play.dice).left.map(rejected).map(play.stepped.tupled)
      case ClientMessage.ChooseWildcard(value) =>
        Turns.chooseWildcard(play.state, value).left.map(rejected).map(chosen =>
          play.stepped(chosen, play.dice)
        )
      case ClientMessage.Surrender => Right(play.stepped(Turns.surrender(play.state), play.dice))
      case ClientMessage.RequestAnalysis => Right(play)

  /** After a placement or a skip: end the game if it is over, else pass the turn. */
  private[session] def advance(state: GameState): GameState =
    val checked = Turns.checkGameOver(state)
    if checked.turn == TurnState.GameOver then checked else Turns.endTurn(checked)

  private def rejected(error: RuleError): ErrorMsg = error match
    case RuleError.WrongState =>
      ErrorMsg(ErrorReason.InvalidAction, "not allowed in this turn state")
    case RuleError.IllegalPlacement => ErrorMsg(ErrorReason.IllegalPlacement, "illegal placement")
    case RuleError.IllegalWildcardValue =>
      ErrorMsg(ErrorReason.IllegalWildcardValue, "wildcard value must be between 1 and 6")
