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
