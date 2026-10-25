package dev.zaksael.rectangles.server.session

import cats.effect.IO
import cats.effect.Ref
import io.circe.Json

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Analysis
import dev.zaksael.rectangles.rules.TurnAnalysis
import dev.zaksael.rectangles.server.protocol.AnalysisMsg
import dev.zaksael.rectangles.server.protocol.ClientMessage
import dev.zaksael.rectangles.server.protocol.ErrorMsg
import dev.zaksael.rectangles.server.protocol.ErrorReason
import dev.zaksael.rectangles.server.protocol.Serialize
import dev.zaksael.rectangles.server.protocol.StateMsg

/**
 * One connection's game: the current play behind a `Ref`, and the replies to client text. With a
 * `bot`, Player Two is played by it, and every reply carries one state per bot step.
 */
final class GameSession private (
    play: Ref[IO, Play],
    bot: Option[BotDifficulty],
    analyse: GameState => Map[Int, TurnAnalysis],
    analysed: Ref[IO, Option[(GameState, Json)]],
) extends Session:
  def state: IO[Vector[Json]] = play.modify(withBotSteps)

  /**
   * The reply to one piece of client text: a `state` message (then one per bot step), or an `error`
   * leaving the game as it was.
   */
  def handle(text: String): IO[Vector[Json]] = ClientMessage.decode(text) match
    case Left(error)                          => IO.pure(Vector(error.toJson))
    case Right(ClientMessage.RequestAnalysis) => analysis
    case Right(message) =>
      play.modify { current =>
        Actions(current, message) match
          case Left(error) => (current, Vector(error.toJson))
          case Right(next) => withBotSteps(next)
      }

  /**
   * The analysis of a finished game, for the requester alone: it changes nothing in the play. The
   * serialized turns are kept for as long as the game is the same state, and computed off the
   * compute pool (a long game with wildcard and enclosure can take a second).
   */
  private def analysis: IO[Vector[Json]] =
    play.get.map(_.state).flatMap { state =>
      if state.turn != TurnState.GameOver then
        IO.pure(Vector(ErrorMsg(ErrorReason.InvalidAction, "the game is not over").toJson))
      else
        analysed.get.flatMap {
          case Some((seen, turns)) if seen == state => IO.pure(Vector(AnalysisMsg(turns).toJson))
          case _ =>
            IO.blocking(Serialize.analysis(analyse(state))).flatMap { turns =>
              analysed.set(Some((state, turns))).as(Vector(AnalysisMsg(turns).toJson))
            }
        }
    }

  /**
   * The state of `current`, then the bot's turn if it is up: the play it ends on and each state.
   */
  private def withBotSteps(current: Play): (Play, Vector[Json]) =
    val (after, steps) = bot.fold((current, Vector.empty[Play]))(BotTurns.run(current, _))
    (after, (current +: steps).map(stateMessage))

private def stateMessage(play: Play): Json =
  StateMsg(Serialize.game(play.state), play.series.fold(Json.Null)(Serialize.series)).toJson

object GameSession:
  def create(
      first: Play,
      bot: Option[BotDifficulty] = None,
      analyse: GameState => Map[Int, TurnAnalysis] = Analysis.turnAnalyses,
  ): IO[GameSession] =
    for
      play     <- Ref.of[IO, Play](first)
      analysed <- Ref.of[IO, Option[(GameState, Json)]](None)
    yield new GameSession(play, bot, analyse, analysed)
