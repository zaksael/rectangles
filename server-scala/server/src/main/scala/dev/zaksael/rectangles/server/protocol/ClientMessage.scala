package dev.zaksael.rectangles.server.protocol

import io.circe.Decoder
import io.circe.Json
import io.circe.parser.parse

import dev.zaksael.rectangles.domain.Cell

enum ClientMessage:
  case Roll
  case Place(topLeft: Cell, width: Int, height: Int)
  case Skip
  case Reroll
  case Surrender
  case RequestAnalysis
  case ContinueSeries
  case ChooseWildcard(value: Int)

object ClientMessage:
  /**
   * Only a JSON number written as a whole number: circe's own `Int` decoder also takes `4.0` and
   * `"4"`.
   */
  private given Decoder[Int] = Decoder[Json].emap(
    _.asNumber.filter(_.toString.matches("-?\\d+")).flatMap(_.toInt).toRight("not a whole number")
  )

  private val malformed = ErrorMsg(ErrorReason.MalformedMessage, "malformed message")

  /** The message in `text`, or the error reply to send when it is not a valid one. */
  def decode(text: String): Either[ErrorMsg, ClientMessage] =
    parse(text).toOption.map(_.hcursor) match
      case None                                              => Left(malformed)
      case Some(cursor) if cursor.get[String]("type").isLeft => Left(malformed)
      case Some(cursor) if !cursor.get[Int]("protocolVersion").contains(Protocol.Version) =>
        Left(ErrorMsg(ErrorReason.ProtocolVersionMismatch, "protocol version mismatch"))
      case Some(cursor) =>
        cursor.get[String]("type").toOption match
          case Some("roll")            => Right(Roll)
          case Some("skip")            => Right(Skip)
          case Some("surrender")       => Right(Surrender)
          case Some("reroll")          => Right(Reroll)
          case Some("requestAnalysis") => Right(RequestAnalysis)
          case Some("continueSeries")  => Right(ContinueSeries)
          case Some("place") =>
            (for
              corner <- cursor.get[(Int, Int)]("topLeft")
              width  <- cursor.get[Int]("width")
              height <- cursor.get[Int]("height")
            yield Place(Cell(corner._1, corner._2), width, height)).left.map(_ => malformed)
          case Some("chooseWildcard") =>
            cursor.get[Int]("value").fold(
              _ => Left(malformed),
              value => Right(ChooseWildcard(value)),
            )
          case _ => Left(malformed)
