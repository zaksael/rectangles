package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

class SetupSpec extends AnyFlatSpec with Matchers:
  "a new game with a pinned starter" should "open with that player and leave the dice alone" in {
    val dice            = ScriptedDice.of(0)
    val (state, remain) = Setup.newGame(Rules(), Some(PlayerId.Two), dice)
    state.current shouldBe PlayerId.Two
    remain shouldBe dice
  }
