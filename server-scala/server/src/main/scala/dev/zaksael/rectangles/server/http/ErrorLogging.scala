package dev.zaksael.rectangles.server.http

import cats.effect.IO
import org.http4s.HttpApp
import org.http4s.Request
import org.http4s.Status

object ErrorLogging:
  private def line(request: Request[IO]): String = s"${request.method} ${request.uri.path}"

  /**
   * Runs `app` and reports each request that ends in a 500 or an exception through `log` (the
   * request line and what went wrong); an exception then fails as before, so the server still
   * answers 500.
   */
  def apply(app: HttpApp[IO], log: (String, String) => IO[Unit]): HttpApp[IO] =
    HttpApp[IO](request =>
      app.run(request).onError(failure => log(line(request), failure.toString)).flatTap(response =>
        IO.whenA(response.status == Status.InternalServerError)(log(line(request), "status 500"))
      )
    )
