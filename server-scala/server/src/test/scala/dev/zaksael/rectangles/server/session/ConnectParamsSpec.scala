package dev.zaksael.rectangles.server.session

import io.circe.Json
import org.http4s.Query
import org.scalatest.EitherValues
import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.server.Draw
import dev.zaksael.rectangles.server.ReplayDice
import dev.zaksael.rectangles.server.protocol.Serialize

class ConnectParamsSpec extends AnyFlatSpec with Matchers with OptionValues with EitherValues:
  "a connect with only the protocol version" should "ask for the default rules" in {
    ConnectParams.parse(Map("protocolVersion" -> "1")) shouldBe Some(Rules())
  }

  it should "take the board size and skip limit it is given" in {
    ConnectParams.parse(Map(
      "protocolVersion" -> "1",
      "boardSize"       -> "23",
      "skipLimit"       -> "3",
    )) shouldBe
      Some(Rules(boardSize = 23, skipLimit = 3))
  }

  "a connect with a house rule turned on" should "ask for that rule" in {
    ConnectParams.parse(Map("protocolVersion" -> "1", "wallsEnabled" -> "true")) shouldBe
      Some(Rules(walls = true))
  }

  "a connect with a parameter that is not allowed" should "be refused" in {
    val refused = Seq(
      "protocolVersion=1&boardSize=20",
      "protocolVersion=1&skipLimit=4",
      "protocolVersion=1&seriesLength=4",
      "protocolVersion=1&botSeats=1",
      "protocolVersion=1&botSeats=2&botDifficulty=Expert",
      "protocolVersion=1&wildcard=1",
      "protocolVersion=1&wildcardEnabled=true",
      "protocolVersion=1&wildcardEnabled=1",
      "protocolVersion=1&wildcardEnabled=maybe",
      "protocolVersion=1&rerollEnabled=true",
      "protocolVersion=1&wallsEnabled=1",
      "protocolVersion=1&obstaclesEnabled=true",
      "protocolVersion=1&prizeEnabled=true",
      "protocolVersion=1&pitfallEnabled=true",
      "protocolVersion=1&stealEnabled=true",
      "protocolVersion=1&prizeEnabled=true&prizePoints=25",
      "protocolVersion=1&selfEnclosedPenaltyEnabled=true",
      "protocolVersion=1&comebackNudgeEnabled=true",
      "",
      "protocolVersion=2",
      "protocolVersion=1&boardSize=abc",
    )
    for query <- refused do
      withClue(query) {
        ConnectParams.parse(Query.unsafeFromString(query).params) shouldBe None
      }
  }

  "a new game" should "start with the player the coin flip picks" in {
    ConnectParams.start(
      Rules(),
      ReplayDice(List(Draw.Choice(2, 1))),
    ).state.current shouldBe PlayerId.Two
    ConnectParams.start(
      Rules(),
      ReplayDice(List(Draw.Choice(2, 0))),
    ).state.current shouldBe PlayerId.One
  }

  it should "start with either player across many games" in {
    val starters = Iterator
      .iterate((Option.empty[PlayerId], SplitMix64(1L): Dice)) { case (_, dice) =>
        val play = ConnectParams.start(Rules(), dice)
        (Some(play.state.current), play.dice)
      }
      .drop(1)
      .take(64)
      .flatMap(_._1)
      .toSet
    starters shouldBe Set(PlayerId.One, PlayerId.Two)
  }

  it should "open as an untouched 19x19 game with the starter to roll" in {
    val rules = ConnectParams.parse(Map("protocolVersion" -> "1")).value
    val game =
      Serialize.game(ConnectParams.start(rules, ReplayDice(List(Draw.Choice(2, 0)))).state).hcursor
    game.downField("board").get[Int]("size").value shouldBe 19
    game.downField("board").get[Int]("skipLimit").value shouldBe 5
    game.downField("turn").get[Int]("currentPlayerId").value shouldBe 1
    game.downField("turn").get[String]("turnState").value shouldBe "awaitingRoll"
    game.downField("turn").get[Json]("lastRoll").value shouldBe Json.Null
    game.downField("gameOver").get[Json]("reason").value shouldBe Json.Null
  }

  "a connect with every house rule explicitly off" should "ask for the default rules, as the web client sends it" in {
    val flags = Seq(
      "wildcardEnabled",
      "rerollEnabled",
      "wallsEnabled",
      "obstaclesEnabled",
      "prizeEnabled",
      "pitfallEnabled",
      "stealEnabled",
      "selfEnclosedPenaltyEnabled",
      "comebackNudgeEnabled",
    )
    val query = ("protocolVersion=1" +: flags.map(flag => s"$flag=false")).mkString("&")
    ConnectParams.parse(Query.unsafeFromString(query).params) shouldBe Some(Rules())
  }
