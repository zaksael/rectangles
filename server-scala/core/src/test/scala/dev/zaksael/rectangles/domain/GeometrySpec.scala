package dev.zaksael.rectangles.domain

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class GeometrySpec extends AnyFlatSpec with Matchers:
  "a rectangle" should "have an area of width times height" in {
    Rectangle(Cell(0, 0), 3, 4, PlayerId.One).area shouldBe 12
  }

  it should "have its bottom right at the far row and column" in {
    Rectangle(Cell(2, 3), 4, 2, PlayerId.One).bottomRight shouldBe Cell(3, 6)
  }

  it should "list every cell it covers" in {
    Rectangle(Cell(1, 1), 2, 2, PlayerId.One).cells.toSet shouldBe
      Set(Cell(1, 1), Cell(1, 2), Cell(2, 1), Cell(2, 2))
  }
