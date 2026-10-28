package dev.zaksael.rectangles.server

import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class GoldenReplaySpec extends AnyFlatSpec with Matchers with EitherValues with OptionValues:
  private val vanilla = Golden.load("vanilla").value

  private def replay(name: String): List[String] =
    GoldenReplay.run(Golden.load(name).value)

  "the vanilla golden set" should "replay with every reply as recorded" in {
    replay("vanilla") shouldBe empty
  }

  "the errors golden set" should "replay with every reply as recorded" in {
    replay("errors") shouldBe empty
  }

  "the series golden set" should "replay with every reply as recorded" in {
    replay("series") shouldBe empty
  }

  "the game-over golden set" should "replay with every reply as recorded, analysis included" in {
    replay("game-over") shouldBe empty
  }

  "the walls golden set" should "replay with every reply as recorded" in {
    replay("walls") shouldBe empty
  }

  "the obstacles golden set" should "replay with every reply as recorded" in {
    replay("obstacles") shouldBe empty
  }

  "the prize golden set" should "replay with every reply as recorded" in {
    replay("prize") shouldBe empty
  }

  "the prize, walls and obstacles golden set" should "replay with every reply as recorded" in {
    replay("prize-walls-obstacles") shouldBe empty
  }

  "the pitfall golden set" should "replay with every reply as recorded" in {
    replay("pitfall") shouldBe empty
  }

  "the steal golden set" should "replay with every reply as recorded" in {
    replay("steal") shouldBe empty
  }

  "the self-enclosed golden set" should "replay with every reply as recorded" in {
    replay("self-enclosed") shouldBe empty
  }

  "the reroll golden set" should "replay with every reply as recorded" in {
    replay("reroll") shouldBe empty
  }

  "the comeback golden set" should "replay with every reply as recorded" in {
    replay("comeback") shouldBe empty
  }

  "the wildcard golden set" should "replay with every reply as recorded" in {
    replay("wildcard") shouldBe empty
  }

  "the all-rules golden set" should "replay with every reply as recorded" in {
    replay("all-rules") shouldBe empty
  }

  "the bot random-starter golden set" should "replay with every reply as recorded" in {
    replay("bot-random-starter") shouldBe empty
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

  it should "name the reply in a bot step whose value changed" in {
    val bot  = Golden.load("bot-random-starter").value
    val step = bot.steps(0)
    val changed = bot.copy(steps =
      bot.steps.updated(
        0,
        step.copy(receive =
          step.receive.updated(
            1,
            step.receive(1).hcursor.downField("game").downField("turn").downField("currentPlayerId")
              .withFocus(_ => Json.fromInt(9)).top.value,
          )
        ),
      )
    )
    GoldenReplay.run(changed).exists(d =>
      d.contains("step 0 reply 1") && d.contains("currentPlayerId")
    ) shouldBe true
  }

  it should "fail when the recording holds a draw the game never made" in {
    GoldenReplay.run(vanilla.copy(draws =
      vanilla.draws :+ Draw.RandInt(1, 6, 3)
    )) should not be empty
  }
