package dev.zaksael.rectangles.server.session

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.Setup
import dev.zaksael.rectangles.rules.SplitMix64

class BotTurnsSpec extends AnyFlatSpec with Matchers:
  "a bot run" should "stop when it is Player One's turn and report every step it took" in {
    val (state, dice) = Setup.newGame(Rules(boardSize = 19), Some(PlayerId.Two), SplitMix64(1L))
    val (end, steps)  = BotTurns.run(Play(state, dice), BotDifficulty.Basic)

    end.state.current shouldBe PlayerId.One
    steps should not be empty
    steps.last shouldBe end
  }
