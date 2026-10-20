package dev.zaksael.rectangles.server

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class SmokeSpec extends AnyFlatSpec with Matchers:
  "server" should "build and run a test" in {
    (1 + 1) shouldBe 2
  }
