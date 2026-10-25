package dev.zaksael.rectangles.server.session

import java.util.concurrent.atomic.AtomicInteger

import cats.effect.IO
import cats.effect.unsafe.implicits.global
import io.circe.Json
import io.circe.parser.parse
import org.scalatest.EitherValues
import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Analysis
import dev.zaksael.rectangles.rules.AnalysisAxis
import dev.zaksael.rectangles.rules.Candidate
import dev.zaksael.rectangles.rules.Series
import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.rules.TurnAnalysis
import dev.zaksael.rectangles.server.Draw
import dev.zaksael.rectangles.server.ReplayDice

class GameSessionSpec extends AnyFlatSpec with Matchers with EitherValues with OptionValues:
  private def session(rolls: Int*): GameSession =
    GameSession
      .create(
        Play(
          GameState.initial(Rules(boardSize = 6)),
          ReplayDice(rolls.toList.map(Draw.RandInt(1, 6, _))),
        )
      )
      .unsafeRunSync()

  /** The one message a session answers with. */
  private def only(messages: IO[Vector[Json]]): Json =
    messages.unsafeRunSync() match
      case Vector(message) => message
      case other           => fail(s"expected one message, got ${other.size}")

  private def turnState(message: Json): String =
    message.hcursor.downField("game").downField("turn").get[String]("turnState").value

  "a new session" should "answer with the state of an untouched game" in {
    val message = only(session().state)
    message.hcursor.get[String]("type").value shouldBe "state"
    message.hcursor.get[Json]("series").value shouldBe Json.Null
    turnState(message) shouldBe "awaitingRoll"
  }

  private def reason(message: Json): String = message.hcursor.get[String]("reason").value

  "handling a roll" should "answer with the state after the roll" in {
    val message = only(session(2, 3).handle("""{"protocolVersion":1,"type":"roll"}"""))
    message.hcursor.get[String]("type").value shouldBe "state"
    turnState(message) shouldBe "choosingPlacement"
  }

  "handling text that is not a message" should "answer with an error and leave the game as it was" in {
    val open  = session(2, 3)
    val error = only(open.handle("not json"))
    error.hcursor.get[String]("type").value shouldBe "error"
    reason(error) shouldBe "malformedMessage"
    turnState(
      only(open.handle("""{"protocolVersion":1,"type":"roll"}"""))
    ) shouldBe "choosingPlacement"
  }

  "handling an action that is not allowed" should "answer with an error and keep the state" in {
    val open = session(2, 3, 4, 5)
    only(open.handle("""{"protocolVersion":1,"type":"roll"}"""))
    val error = only(open.handle("""{"protocolVersion":1,"type":"roll"}"""))
    reason(error) shouldBe "invalidAction"
    turnState(only(open.state)) shouldBe "choosingPlacement"
  }

  "a session where the bot moves first" should "open with the bot's whole turn, one state per step" in {
    val botFirst = GameSession
      .create(
        Play(GameState.initial(Rules(boardSize = 6), PlayerId.Two), SplitMix64(7L)),
        Some(BotDifficulty.Basic),
      )
      .unsafeRunSync()
    val opening = botFirst.state.unsafeRunSync()
    opening.map(turnState) shouldBe Vector("awaitingRoll", "choosingPlacement", "awaitingRoll")
    opening.map(
      _.hcursor.downField("game").downField("turn").get[Int]("currentPlayerId").value
    ) shouldBe
      Vector(2, 2, 1)
  }

  "a dead roll with a reroll charge left" should "wait for the skip to be sent before recording it" in {
    val stuck = GameSession
      .create(
        Play(
          GameState.initial(Rules(boardSize = 2, reroll = true)),
          ReplayDice(List(Draw.RandInt(1, 6, 6), Draw.RandInt(1, 6, 6))),
        )
      )
      .unsafeRunSync()
    val rolled = only(stuck.handle("""{"protocolVersion":1,"type":"roll"}"""))
    turnState(rolled) shouldBe "skipped"
    rolled.hcursor.downField(
      "game"
    ).downField("turn").get[List[Json]]("recentTurns").value shouldBe empty
    val skipped = only(stuck.handle("""{"protocolVersion":1,"type":"skip"}"""))
    val game    = skipped.hcursor.downField("game")
    game.downField("turn").get[List[Json]]("recentTurns").value should have size 1
    game.downField(
      "players"
    ).downField("1").downField("board").get[Int]("consecutiveSkips").value shouldBe 1
  }

  private val flagged =
    Map(3 -> TurnAnalysis(AnalysisAxis.Prize, 0, 10, Candidate(Cell(0, 0), 4, 1)))

  private val flaggedTurns =
    parse(
      """[{"turn":3,"axis":"prize","chosen":0,"best":10,"topLeft":[0,0],"width":4,"height":1}]"""
    ).value

  private val surrender = """{"protocolVersion":1,"type":"surrender"}"""
  private val request   = """{"protocolVersion":1,"type":"requestAnalysis"}"""

  /** A fresh game, already surrendered, whose analysis is `analyse`. */
  private def finished(
      analyse: GameState => Map[Int, TurnAnalysis] = Analysis.turnAnalyses,
      bot: Option[BotDifficulty] = None,
  ): GameSession =
    val over = GameSession
      .create(Play(GameState.initial(Rules(boardSize = 6)), SplitMix64(1L)), bot, analyse)
      .unsafeRunSync()
    over.handle(surrender).unsafeRunSync()
    over

  "a request for analysis after the game is over" should "answer the requester with the turns" in {
    val reply = only(finished(_ => flagged).handle(request))
    reply.hcursor.get[String]("type").value shouldBe "analysis"
    reply.hcursor.get[Json]("turns").value shouldBe flaggedTurns
  }

  it should "answer an empty list when nothing is flagged" in {
    only(finished().handle(request)).hcursor.get[Json]("turns").value shouldBe Json.arr()
  }

  it should "be computed once for the same game" in {
    val calls = AtomicInteger(0)
    val counted = finished { _ =>
      calls.incrementAndGet()
      flagged
    }
    (1 to 2).foreach(_ =>
      only(counted.handle(request)).hcursor.get[Json]("turns").value shouldBe flaggedTurns
    )
    calls.get shouldBe 1
  }

  it should "also answer for a finished game against the bot" in {
    only(finished(bot = Some(BotDifficulty.Basic)).handle(request)).hcursor
      .get[String]("type").value shouldBe "analysis"
  }

  "a request for analysis mid-game" should "be an invalid action and leave the game playable" in {
    val open  = session(2, 3)
    val error = only(open.handle(request))
    error.hcursor.get[String]("type").value shouldBe "error"
    reason(error) shouldBe "invalidAction"
    turnState(only(open.handle(surrender))) shouldBe "gameOver"
  }

  private def seriesOf(message: Json) = message.hcursor.downField("series")

  /** The session a connect for `query` opens, with the dice fixed. */
  private def connected(
      query: Map[String, String],
      bot: Option[BotDifficulty] = None,
  ): GameSession =
    val connect = ConnectParams.parse(Map("protocolVersion" -> "1") ++ query).value
    GameSession
      .create(ConnectParams.open(connect, SplitMix64(3L)), bot)
      .unsafeRunSync()

  "a connect with a series length" should "open on a series with no round played" in {
    val series = seriesOf(only(connected(Map("seriesLength" -> "3")).state))
    series.get[Int]("length").value shouldBe 3
    series.get[Int]("gamesPlayed").value shouldBe 0
    series.get[Boolean]("isComplete").value shouldBe false
  }

  it should "keep the house rules it is given" in {
    val game = only(connected(Map("seriesLength" -> "3", "prizeEnabled" -> "true")).state)
      .hcursor.downField("game")
    game.downField("houseRules").downField("prize").get[Boolean]("enabled").value shouldBe true
  }

  "a finished round of a series" should "be recorded in the series" in {
    val open   = connected(Map("seriesLength" -> "3"))
    val series = seriesOf(only(open.handle(surrender)))
    series.get[Int]("gamesPlayed").value shouldBe 1
    series.get[List[Json]]("rounds").value should have size 1
  }

  it should "be recorded when a bot move ends it" in {
    val stuck = Play(
      GameState.initial(Rules(boardSize = 19, skipLimit = 1), PlayerId.Two).copy(
        turn = TurnState.Skipped
      ),
      SplitMix64(1L),
      Some(Series(3, Rules(boardSize = 19, skipLimit = 1))),
    )
    val replies = GameSession.create(stuck, Some(BotDifficulty.Basic)).unsafeRunSync()
      .state.unsafeRunSync()

    turnState(replies.last) shouldBe "gameOver"
    seriesOf(replies.last).get[Int]("gamesPlayed").value shouldBe 1
  }
