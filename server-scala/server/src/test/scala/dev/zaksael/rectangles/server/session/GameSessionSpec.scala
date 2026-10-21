package dev.zaksael.rectangles.server.session

import cats.effect.unsafe.implicits.global
import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Rules
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

  private def turnState(message: Json): String =
    message.hcursor.downField("game").downField("turn").get[String]("turnState").value

  "a new session" should "answer with the state of an untouched game" in {
    val message = session().state.unsafeRunSync()
    message.hcursor.get[String]("type").value shouldBe "state"
    message.hcursor.get[Json]("series").value shouldBe Json.Null
    turnState(message) shouldBe "awaitingRoll"
  }

  private def reason(message: Json): String = message.hcursor.get[String]("reason").value

  "handling a roll" should "answer with the state after the roll" in {
    val message = session(2, 3).handle("""{"protocolVersion":1,"type":"roll"}""").unsafeRunSync()
    message.hcursor.get[String]("type").value shouldBe "state"
    turnState(message) shouldBe "choosingPlacement"
  }

  "handling text that is not a message" should "answer with an error and leave the game as it was" in {
    val open  = session(2, 3)
    val error = open.handle("not json").unsafeRunSync()
    error.hcursor.get[String]("type").value shouldBe "error"
    reason(error) shouldBe "malformedMessage"
    turnState(
      open.handle("""{"protocolVersion":1,"type":"roll"}""").unsafeRunSync()
    ) shouldBe "choosingPlacement"
  }

  "handling an action that is not allowed" should "answer with an error and keep the state" in {
    val open = session(2, 3, 4, 5)
    open.handle("""{"protocolVersion":1,"type":"roll"}""").unsafeRunSync()
    val error = open.handle("""{"protocolVersion":1,"type":"roll"}""").unsafeRunSync()
    reason(error) shouldBe "invalidAction"
    turnState(open.state.unsafeRunSync()) shouldBe "choosingPlacement"
  }
