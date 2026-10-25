package dev.zaksael.rectangles.server.protocol

import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell

class ProtocolSpec extends AnyFlatSpec with Matchers with EitherValues:
  "a roll message" should "decode" in {
    ClientMessage.decode(
      """{"protocolVersion":1,"type":"roll"}"""
    ).value shouldBe ClientMessage.Roll
  }

  "a skip message" should "decode" in {
    ClientMessage.decode(
      """{"protocolVersion":1,"type":"skip"}"""
    ).value shouldBe ClientMessage.Skip
  }

  "a surrender message" should "decode" in {
    ClientMessage.decode(
      """{"protocolVersion":1,"type":"surrender"}"""
    ).value shouldBe ClientMessage.Surrender
  }

  "a reroll message" should "decode" in {
    ClientMessage.decode(
      """{"protocolVersion":1,"type":"reroll"}"""
    ).value shouldBe ClientMessage.Reroll
  }

  "a place message" should "decode with its top-left and size" in {
    ClientMessage
      .decode("""{"protocolVersion":1,"type":"place","topLeft":[2,3],"width":4,"height":5}""")
      .value shouldBe ClientMessage.Place(Cell(2, 3), 4, 5)
  }

  "a state message" should "carry its series" in {
    val game   = Json.obj("board" -> Json.obj("size" -> Json.fromInt(19)))
    val series = Json.obj("length" -> Json.fromInt(3))
    StateMsg(game, series).toJson shouldBe Json.obj(
      "protocolVersion" -> Json.fromInt(1),
      "type"            -> Json.fromString("state"),
      "game"            -> game,
      "series"          -> series,
    )
  }

  "a request-analysis message" should "decode" in {
    ClientMessage.decode(
      """{"protocolVersion":1,"type":"requestAnalysis"}"""
    ).value shouldBe ClientMessage.RequestAnalysis
  }

  "an analysis message" should "encode its turns" in {
    val turns = Json.arr(Json.obj("turn" -> Json.fromInt(1)))
    AnalysisMsg(turns).toJson shouldBe Json.obj(
      "protocolVersion" -> Json.fromInt(1),
      "type"            -> Json.fromString("analysis"),
      "turns"           -> turns,
    )
  }

  "a choose-wildcard message" should "decode with its value" in {
    ClientMessage
      .decode("""{"protocolVersion":1,"type":"chooseWildcard","value":4}""")
      .value shouldBe ClientMessage.ChooseWildcard(4)
  }

  "an error message" should "encode its reason name and message" in {
    ErrorMsg(ErrorReason.IllegalPlacement, "nope").toJson shouldBe Json.obj(
      "protocolVersion" -> Json.fromInt(1),
      "type"            -> Json.fromString("error"),
      "reason"          -> Json.fromString("illegalPlacement"),
      "message"         -> Json.fromString("nope"),
    )
  }

  "text that is not JSON" should "be a malformed message" in {
    ClientMessage.decode("not json").left.value.reason shouldBe ErrorReason.MalformedMessage
  }

  "a message without a type" should "be a malformed message" in {
    ClientMessage.decode(
      """{"protocolVersion":1}"""
    ).left.value.reason shouldBe ErrorReason.MalformedMessage
  }

  "a message with another protocol version" should "be a version mismatch, even when its type is unknown" in {
    ClientMessage.decode("""{"protocolVersion":2,"type":"roll"}""").left.value.reason shouldBe
      ErrorReason.ProtocolVersionMismatch
    ClientMessage.decode("""{"protocolVersion":2,"type":"nonsense"}""").left.value.reason shouldBe
      ErrorReason.ProtocolVersionMismatch
  }

  "a choose-wildcard value that is not a whole JSON number" should "be a malformed message" in {
    for value <- Seq(""""4"""", "4.0", "true", "[4]", "null") do
      withClue(value) {
        ClientMessage
          .decode(s"""{"protocolVersion":1,"type":"chooseWildcard","value":$value}""")
          .left
          .value
          .reason shouldBe ErrorReason.MalformedMessage
      }
  }

  "a place message with a bad field" should "be a malformed message" in {
    val bad = Seq(
      """"topLeft":[[0],[0]],"width":2,"height":2""",
      """"topLeft":["0","0"],"width":2,"height":2""",
      """"topLeft":[0],"width":2,"height":2""",
      """"topLeft":[0,0],"width":[2],"height":2""",
      """"topLeft":[0,0],"width":2.0,"height":2""",
      """"topLeft":[0,0],"width":true,"height":2""",
    )
    for fields <- bad do
      withClue(fields) {
        ClientMessage
          .decode(s"""{"protocolVersion":1,"type":"place",$fields}""")
          .left
          .value
          .reason shouldBe ErrorReason.MalformedMessage
      }
  }

  "a message with an unknown type" should "be a malformed message" in {
    ClientMessage.decode("""{"protocolVersion":1,"type":"nonsense"}""").left.value.reason shouldBe
      ErrorReason.MalformedMessage
  }
