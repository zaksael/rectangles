package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class DiceSpec extends AnyFlatSpec with Matchers:
  "SplitMix64" should "match the reference sequence for seed 0" in {
    val (first, rest) = SplitMix64(0L).nextLong
    first shouldBe 0xe220a8397b1dcdafL
    rest.nextLong._1 shouldBe 0x6e789e6aa1b965f4L
  }

  it should "draw values within the asked range, both ends reachable" in {
    val draws = Iterator.iterate((0, SplitMix64(7L): Dice)) { case (_, dice) => dice.between(1, 6) }
    val values = draws.drop(1).take(200).map(_._1).toSet
    values shouldBe Set(1, 2, 3, 4, 5, 6)
  }
