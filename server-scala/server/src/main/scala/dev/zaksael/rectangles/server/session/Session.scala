package dev.zaksael.rectangles.server.session

import cats.effect.IO
import io.circe.Json

/**
 * What the route needs from one connection's game: its opening state and a reply to each client
 * text.
 */
trait Session:
  def state: IO[Json]
  def handle(text: String): IO[Json]
