package dev.zaksael.rectangles.domain

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class SeatsSpec extends AnyFlatSpec with Matchers:
  private val seats = Seats("first", "second")

  "a seat" should "be read by its player" in {
    seats(PlayerId.One) shouldBe "first"
    seats(PlayerId.Two) shouldBe "second"
  }

  it should "be replaced for its player only" in {
    seats.updated(PlayerId.Two, "new") shouldBe Seats("first", "new")
    seats.updated(PlayerId.One, "new") shouldBe Seats("new", "second")
  }

  "mapping the seats" should "apply the function to each seat, keeping their order" in {
    seats.map(_.length) shouldBe Seats(5, 6)
  }

  "the seats' values" should "list Player One's first" in {
    seats.values shouldBe Vector("first", "second")
  }

  "the seats as a map" should "hold both players" in {
    seats.toMap shouldBe Map(PlayerId.One -> "first", PlayerId.Two -> "second")
  }
