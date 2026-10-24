package dev.zaksael.rectangles.server.session

import cats.effect.IO
import io.circe.Json

/**
 * What the route needs from one connection's game: its opening messages and the messages that
 * answer each client text, in the order they are sent.
 */
trait Session:
  def state: IO[Vector[Json]]
  def handle(text: String): IO[Vector[Json]]
