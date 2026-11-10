package dev.zaksael.rectangles.rules

import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.Seats

class BotMatchSpec extends AnyFlatSpec with Matchers with OptionValues:
  private val small  = Rules(boardSize = 6)
  private val greedy = Seats(BotDifficulty.Greedy, BotDifficulty.Greedy)

  "a bot match" should "play to the end and score both seats" in {
    val result = BotMatch.play(small, greedy, Some(PlayerId.One), SplitMix64(1L)).value

    result.scores.values.forall(_ > 0) shouldBe true
  }

  it should "give the same result for the same seed" in {
    val play = () => BotMatch.play(small, greedy, Some(PlayerId.One), SplitMix64(7L))

    play() shouldBe play()
  }

  it should "play each seat at its own difficulty" in {
    val blockingWins = (1L to 30L).count { seed =>
      val blockingSeat = if seed % 2 == 0 then PlayerId.One else PlayerId.Two
      val seats = Seats(
        BotDifficulty.Basic,
        BotDifficulty.Basic,
      ).updated(blockingSeat, BotDifficulty.Blocking)
      BotMatch.play(
        small,
        seats,
        Some(PlayerId.One),
        SplitMix64(seed),
      ).value.winner.contains(blockingSeat)
    }

    blockingWins should be >= 20
  }
