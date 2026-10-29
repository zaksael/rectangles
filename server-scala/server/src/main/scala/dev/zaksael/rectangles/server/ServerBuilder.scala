package dev.zaksael.rectangles.server

import cats.effect.IO
import org.http4s.ember.server.EmberServerBuilder

import dev.zaksael.rectangles.server.http.WsRoutes

object ServerBuilder:
  /** Ember with the settings the real server and the tests must share. */
  val ember: EmberServerBuilder[IO] =
    EmberServerBuilder.default[IO].withMaxWebSocketMessageSize(WsRoutes.maxMessageSize)
