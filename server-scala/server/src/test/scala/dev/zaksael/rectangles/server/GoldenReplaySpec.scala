package dev.zaksael.rectangles.server

import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class GoldenReplaySpec extends AnyFlatSpec with Matchers with EitherValues:
  private val vanilla = Golden.load("vanilla").value

  private def replay(name: String, pending: Map[Int, String] = Map.empty): List[String] =
    GoldenReplay.run(Golden.load(name).value, pending)

  "the vanilla golden set" should "replay with every reply as recorded" in {
    replay("vanilla") shouldBe empty
  }

  // Steps 10 and 11 send messages the server cannot answer yet: each owner deletes its own entry.
  "the errors golden set" should "replay with every reply as recorded, but the steps still pending" in {
    replay(
      "errors",
      Map(10 -> "requestAnalysis (F4)", 11 -> "continueSeries (G3)"),
    ) shouldBe empty
  }

  "the golden replay runner" should "report a changed score value" in {
    val changed = vanilla.copy(steps =
      vanilla.steps.updated(
        2,
        vanilla.steps(2).copy(receive = vanilla.steps(2).receive.map { reply =>
          reply.hcursor.downField("game").downField("players").downField("1").downField("score")
            .downField("totalScore").withFocus(_ => Json.fromInt(11)).top.getOrElse(reply)
        }),
      )
    )
    GoldenReplay.run(changed).exists(_.contains("totalScore")) shouldBe true
  }

  it should "fail when the recording holds a draw the game never made" in {
    GoldenReplay.run(vanilla.copy(draws =
      vanilla.draws :+ Draw.RandInt(1, 6, 3)
    )) should not be empty
  }
