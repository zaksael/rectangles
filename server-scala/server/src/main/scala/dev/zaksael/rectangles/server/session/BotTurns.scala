package dev.zaksael.rectangles.server.session

import scala.annotation.tailrec

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.BotMatch

/** The bot's moves for Player Two, one atomic action per step so each can be sent on its own. */
object BotTurns:
  /** None when the game is over, or when the action the bot picked is refused. */
  def step(play: Play, difficulty: BotDifficulty): Option[Play] =
    BotMatch.step(play.state, difficulty, play.dice).map(play.stepped.tupled)

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
