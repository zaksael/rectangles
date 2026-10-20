package dev.zaksael.rectangles

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class SmokeSpec extends AnyFlatSpec with Matchers:
  "core" should "build and run a test" in {
    (1 + 1) shouldBe 2
  }
