package dev.zaksael.rectangles.server

import io.circe.parser.parse
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class JsonDiffSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def json(text: String) = parse(text).value

  "a diff" should "name the path of a changed value and of a missing or extra key" in {
    JsonDiff.diff(
      json("""{"a":{"b":1,"c":2}}"""),
      json("""{"a":{"b":2,"d":2}}"""),
    ) should contain theSameElementsAs List(
      "$.a.b: expected 1, got 2",
      "$.a.c: missing",
      "$.a.d: unexpected",
    )
  }

  it should "be empty for equal documents" in {
    JsonDiff.diff(json("""{"a":[1,{"b":null}]}"""), json("""{"a":[1,{"b":null}]}""")) shouldBe empty
  }

  it should "compare a topLefts or edges list without regard to order" in {
    JsonDiff.diff(
      json("""{"topLefts":[[0,1],[2,3]]}"""),
      json("""{"topLefts":[[2,3],[0,1]]}"""),
    ) shouldBe empty
    JsonDiff.diff(
      json("""{"edges":[[[0,1],[0,2]],[[2,3],[3,3]]]}"""),
      json("""{"edges":[[[2,3],[3,3]],[[0,1],[0,2]]]}"""),
    ) shouldBe empty
    JsonDiff.diff(
      json("""{"x":[[0,1],[2,3]]}"""),
      json("""{"x":[[2,3],[0,1]]}"""),
    ) should not be empty
  }
