package dev.zaksael.rectangles.server.session

import scala.annotation.tailrec

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Bot
import dev.zaksael.rectangles.rules.Turns

/** The bot's moves for Player Two, one atomic action per step so each can be sent on its own. */
object BotTurns:
  /** None when the game is over, or when the action the bot picked is refused. */
  def step(play: Play, difficulty: BotDifficulty): Option[Play] =
    val state = play.state
    if Bot.shouldReroll(state, difficulty) then
      Turns.reroll(state, play.dice).toOption.map(play.stepped.tupled)
    else
      state.turn match
        case TurnState.AwaitingRoll =>
          Turns.rollDice(state, play.dice).toOption.map(play.stepped.tupled)
        case TurnState.ChoosingWildcard =>
          val (value, next) = Bot.chooseWildcardValue(state, difficulty, play.dice)
          Turns.chooseWildcard(state, value).toOption.map(play.stepped(_, next))
        case TurnState.ChoosingPlacement =>
          val (pick, next) = Bot.choosePlacement(state, difficulty, play.dice)
          Turns.attemptPlace(state, pick.topLeft, pick.width, pick.height).toOption.map(placed =>
            play.stepped(Actions.advance(placed), next)
          )
        case TurnState.Skipped =>
          Turns.confirmSkip(state).toOption.map(skipped =>
            play.stepped(Actions.advance(skipped), play.dice)
          )
        case TurnState.GameOver => None

  /** Steps while it is Player Two's turn; the play it ends on and the play after every step. */
  def run(play: Play, difficulty: BotDifficulty): (Play, Vector[Play]) =
    @tailrec def go(current: Play, states: Vector[Play]): (Play, Vector[Play]) =
      if current.state.turn == TurnState.GameOver || current.state.current != PlayerId.Two then
        (current, states)
      else
        step(current, difficulty) match
          case None       => (current, states)
          case Some(next) => go(next, states :+ next)
    go(play, Vector.empty)
