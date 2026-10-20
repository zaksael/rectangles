package dev.zaksael.rectangles.server

import cats.effect.IO
import cats.effect.IOApp
import cats.implicits.toSemigroupKOps
import logging4s.cats.CatsInstances.given
import logging4s.console.ConsoleInstances.given
import logging4s.core.Logging
import logging4s.core.syntax.loggable.*
import org.http4s.ember.server.EmberServerBuilder

import dev.zaksael.rectangles.server.http.HealthRoutes
import dev.zaksael.rectangles.server.http.WsRoutes

object Main extends IOApp.Simple:
  def run: IO[Unit] =
    for
      log    <- Logging.create[IO]("Main")
      config <- Config.load
      _ <- EmberServerBuilder
        .default[IO]
        .withHost(config.host)
        .withPort(config.port)
        .withHttpWebSocketApp(ws => (HealthRoutes.routes <+> WsRoutes.routes(ws)).orNotFound)
        .build
        .use(server =>
          log.info("listening", server.address.toString.asLogValue("address")) *> IO.never
        )
    yield ()
