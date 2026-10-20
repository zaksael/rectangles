package dev.zaksael.rectangles.domain

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class PlayersSpec extends AnyFlatSpec with Matchers:
  private val fresh = Player(PlayerId.One, "Player 1", Cell(0, 0))

  "a player" should "sum the area of its pieces" in {
    val pieces = Vector(
      Rectangle(Cell(0, 0), 2, 3, PlayerId.One),
      Rectangle(Cell(2, 0), 1, 1, PlayerId.One),
    )
    fresh.copy(pieces = pieces).totalArea shouldBe 7
  }

  it should "have moved once it holds a piece" in {
    fresh.hasMoved shouldBe false
    fresh.copy(pieces = Vector(Rectangle(Cell(0, 0), 1, 1, PlayerId.One))).hasMoved shouldBe true
  }

  it should "have no area without pieces" in {
    fresh.totalArea shouldBe 0
  }

  it should "start with no special captures" in {
    fresh.specialCaptures shouldBe Map.empty
  }

  "a score breakdown" should "total its signed parts" in {
    ScoreBreakdown(
      area = 73,
      prize = 10,
      pitfall = -20,
      steal = 10,
      enclosure = -2,
    ).total shouldBe 71
  }
