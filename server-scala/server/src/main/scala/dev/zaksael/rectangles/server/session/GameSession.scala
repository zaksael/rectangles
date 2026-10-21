package dev.zaksael.rectangles.server.session

import cats.effect.IO
import cats.effect.Ref
import io.circe.Json

import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.server.protocol.ClientMessage
import dev.zaksael.rectangles.server.protocol.Serialize
import dev.zaksael.rectangles.server.protocol.StateMsg

/** One connection's game: the current play behind a `Ref`, and the replies to client text. */
final class GameSession private (play: Ref[IO, Play]):
  def state: IO[Json] = play.get.map(current => stateMessage(current.state))

  /**
   * The reply to one piece of client text: a `state` message, or an `error` leaving the game as it
   * was.
   */
  def handle(text: String): IO[Json] = ClientMessage.decode(text) match
    case Left(error) => IO.pure(error.toJson)
    case Right(message) =>
      play.modify { current =>
        Actions(current, message) match
          case Left(error) => (current, error.toJson)
          case Right(next) => (next, stateMessage(next.state))
      }

private def stateMessage(state: GameState): Json = StateMsg(Serialize.game(state)).toJson

object GameSession:
  def create(first: Play): IO[GameSession] = Ref.of[IO, Play](first).map(new GameSession(_))
