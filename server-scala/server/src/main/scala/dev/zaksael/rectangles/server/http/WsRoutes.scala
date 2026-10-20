package dev.zaksael.rectangles.server.http

import cats.effect.IO
import fs2.Stream
import io.circe.Json
import org.http4s.HttpRoutes
import org.http4s.dsl.io.*
import org.http4s.server.websocket.WebSocketBuilder2
import org.http4s.websocket.WebSocketFrame

object WsRoutes:
  private val stubState: Json = Json.obj("protocolVersion" -> Json.fromInt(1), "type" -> Json.fromString("state"))

  /** Placeholder: sends one hand-built state message, then ignores the client and stays open. */
  def routes(ws: WebSocketBuilder2[IO]): HttpRoutes[IO] = HttpRoutes.of[IO] { case GET -> Root / "ws" =>
    ws.build(Stream.emit(WebSocketFrame.Text(stubState.noSpaces)) ++ Stream.never[IO], _.drain)
  }
