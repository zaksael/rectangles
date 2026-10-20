package dev.zaksael.rectangles.domain

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class TurnsSpec extends AnyFlatSpec with Matchers:
  "a turn record" should "store a skip as no placement" in {
    val record = TurnRecord(PlayerId.One, Roll(4, 5), None)
    record.placed shouldBe None
    record.roll shouldBe Roll(4, 5)
  }

  it should "store the placed rectangle" in {
    val rectangle = Rectangle(Cell(0, 0), 2, 2, PlayerId.One)
    TurnRecord(PlayerId.One, Roll(2, 2), Some(rectangle)).placed shouldBe Some(rectangle)
  }
