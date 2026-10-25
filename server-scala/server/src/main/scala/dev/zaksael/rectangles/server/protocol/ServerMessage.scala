package dev.zaksael.rectangles.server.protocol

import io.circe.Json

object Protocol:
  val Version: Int = 1

final case class ErrorMsg(reason: ErrorReason, message: String):
  def toJson: Json = Json.obj(
    "protocolVersion" -> Json.fromInt(Protocol.Version),
    "type"            -> Json.fromString("error"),
    "reason"          -> Json.fromString(reason.wire),
    "message"         -> Json.fromString(message),
  )

/** `game` is `Serialize.game`; `series` is `Serialize.series`, or null outside a series. */
final case class StateMsg(game: Json, series: Json = Json.Null):
  def toJson: Json = Json.obj(
    "protocolVersion" -> Json.fromInt(Protocol.Version),
    "type"            -> Json.fromString("state"),
    "game"            -> game,
    "series"          -> series,
  )

/** `turns` is `Serialize.analysis`. */
final case class AnalysisMsg(turns: Json):
  def toJson: Json = Json.obj(
    "protocolVersion" -> Json.fromInt(Protocol.Version),
    "type"            -> Json.fromString("analysis"),
    "turns"           -> turns,
  )
