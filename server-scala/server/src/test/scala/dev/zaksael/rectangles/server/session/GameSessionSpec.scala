package dev.zaksael.rectangles.server.session

import cats.effect.IO
import cats.effect.unsafe.implicits.global
import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.server.Draw
import dev.zaksael.rectangles.server.ReplayDice

class GameSessionSpec extends AnyFlatSpec with Matchers with EitherValues:
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
