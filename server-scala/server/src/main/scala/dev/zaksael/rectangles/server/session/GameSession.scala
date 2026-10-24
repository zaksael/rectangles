package dev.zaksael.rectangles.server.session

import cats.effect.IO
import cats.effect.Ref
import io.circe.Json

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.server.protocol.ClientMessage
import dev.zaksael.rectangles.server.protocol.Serialize
import dev.zaksael.rectangles.server.protocol.StateMsg

/**
 * One connection's game: the current play behind a `Ref`, and the replies to client text. With a
 * `bot`, Player Two is played by it, and every reply carries one state per bot step.
 */
final class GameSession private (play: Ref[IO, Play], bot: Option[BotDifficulty]) extends Session:
  def state: IO[Vector[Json]] = play.modify(withBotSteps)

  /**
   * The reply to one piece of client text: a `state` message (then one per bot step), or an `error`
   * leaving the game as it was.
   */
  def handle(text: String): IO[Vector[Json]] = ClientMessage.decode(text) match
    case Left(error) => IO.pure(Vector(error.toJson))
    case Right(message) =>
      play.modify { current =>
        Actions(current, message) match
          case Left(error) => (current, Vector(error.toJson))
          case Right(next) => withBotSteps(next)
      }

  /**
   * The state of `current`, then the bot's turn if it is up: the play it ends on and each state.
   */
  private def withBotSteps(current: Play): (Play, Vector[Json]) =
    val (after, steps) = bot.fold((current, Vector.empty[GameState]))(BotTurns.run(current, _))
    (after, (current.state +: steps).map(stateMessage))

private def stateMessage(state: GameState): Json = StateMsg(Serialize.game(state)).toJson

object GameSession:
  def create(first: Play, bot: Option[BotDifficulty] = None): IO[GameSession] =
    Ref.of[IO, Play](first).map(new GameSession(_, bot))
