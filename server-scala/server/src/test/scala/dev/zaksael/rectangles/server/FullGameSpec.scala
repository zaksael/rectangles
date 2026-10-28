package dev.zaksael.rectangles.server

import scala.annotation.tailrec

import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.server.http.WsRoutes

/**
 * Whole games over a real socket with every house rule on: a scripted human (the first legal move
 * of whatever the turn asks) against the bot. A crash-class guard, not a rules test: it checks the
 * game ends, the replayed history lands on the live scores, and the analysis reply is well formed.
 */
class FullGameSpec extends AnyFlatSpec with Matchers with EitherValues with OptionValues:
  private val MaxSteps = 5000

  private val allRules = List(
    "wildcardEnabled",
    "rerollEnabled",
    "wallsEnabled",
    "obstaclesEnabled",
    "prizeEnabled",
    "pitfallEnabled",
    "stealEnabled",
    "selfEnclosedPenaltyEnabled",
    "comebackNudgeEnabled",
  ).map(rule => s"$rule=true").mkString("&")

  private def turn(state: Json) = state.hcursor.downField("game").downField("turn")

  private def over(state: Json): Boolean = turn(state).get[String]("turnState").value == "gameOver"

  private def humanToAct(state: Json): Boolean =
    over(state) || turn(state).get[Int]("currentPlayerId").value == 1

  /** The messages up to the first one that leaves the human to act, or the game over. */
  @tailrec
  private def untilHuman(client: WsTestClient): Json =
    val message = client.next()
    if humanToAct(message) then message
    else untilHuman(client)

  private def humanAction(state: Json): String =
    val game = state.hcursor.downField("game")
    val spot = turn(state).downField("legalPlacements").downArray
    val body = turn(state).get[String]("turnState").value match
      case "awaitingRoll" => """"type":"roll""""
      case "choosingWildcard" =>
        val value = game.downField("houseRules").downField("wildcard").downField(
          "legalValues"
        ).downArray.as[Int].value
        s""""type":"chooseWildcard","value":$value"""
      case "choosingPlacement" =>
        val top = spot.downField("topLefts").downArray
        s""""type":"place","topLeft":[${top.downN(0).as[Int].value},${top.downN(
            1
          ).as[Int].value}],""" +
          s""""width":${spot.get[Int]("width").value},"height":${spot.get[Int]("height").value}"""
      case _ => """"type":"skip""""
    s"""{"protocolVersion":1,$body}"""

  @tailrec
  private def finish(client: WsTestClient, state: Json, steps: Int): Json =
    if over(state) then state
    else if steps >= MaxSteps then fail(s"the game was still running after $MaxSteps moves")
    else
      client.send(humanAction(state))
      finish(client, untilHuman(client), steps + 1)

  private def play(difficulty: String, boardSize: Int): Unit =
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val query =
        s"protocolVersion=1&boardSize=$boardSize&botSeats=2&botDifficulty=$difficulty&$allRules"
      val client = WsTestClient.connect(port, query).value
      try
        val end      = finish(client, untilHuman(client), 0)
        val gameOver = end.hcursor.downField("game").downField("gameOver")
        gameOver.get[String]("reason").value should not be empty

        val history = gameOver.get[List[Json]]("history").value
        history should not be empty
        val players = end.hcursor.downField("game").downField("players")
        for who <- List("1", "2") do
          val live = players.downField(who).downField("score")
          val last = history.last.hcursor
          last.downField("score").get[Int](who).value shouldBe live.get[Int]("totalScore").value
          last.downField("breakdown").downField(who).focus.value shouldBe
            live.downField("breakdown").focus.value

        client.send("""{"protocolVersion":1,"type":"requestAnalysis"}""")
        val analysis = client.next()
        analysis.hcursor.get[String]("type").value shouldBe "analysis"
        val turns =
          analysis.hcursor.get[List[Json]]("turns").value.map(_.hcursor.get[Int]("turn").value)
        turns shouldBe turns.sorted
        all(turns) should (be >= 1 and be <= history.size): Unit
      finally client.close()
    }

  for (difficulty, boardSize) <-
      List(("Basic", 19), ("Greedy", 19), ("Blocking", 19), ("Greedy", 27))
  do
    s"a full game against the $difficulty bot on $boardSize x $boardSize with every rule on" should
      "play through, replay to its live scores and serialize its analysis" in play(
        difficulty,
        boardSize,
      )
