package dev.zaksael.rectangles.server.http

import java.nio.file.Files
import java.nio.file.Path

import cats.data.OptionT
import cats.effect.IO
import org.http4s.Header
import org.http4s.HttpRoutes
import org.http4s.Request
import org.http4s.Response
import org.http4s.Status
import org.http4s.server.staticcontent.FileService
import org.http4s.server.staticcontent.fileService
import org.typelevel.ci.*

object StaticRoutes:
  private val hardening = List(
    Header.Raw(ci"X-Frame-Options", "DENY"),
    Header.Raw(ci"X-Content-Type-Options", "nosniff"),
  )

  /**
   * Files under `/assets/` carry a content hash in their name, so they never change; the rest must
   * revalidate, and so does any answer that is not the file itself (a 304 for it counts as the
   * file).
   */
  private def caching(request: Request[IO], response: Response[IO]): Header.Raw =
    val isFile   = response.status == Status.Ok || response.status == Status.NotModified
    val isHashed = request.uri.path.renderString.startsWith("/assets/")
    if isFile && isHashed then Header.Raw(ci"Cache-Control", "public, max-age=31536000, immutable")
    else Header.Raw(ci"Cache-Control", "no-cache")

  /**
   * The built frontend in `dist` at `/`: `index.html` at the root, the assets, and 404 for any
   * other path (the app has no client routes). Every response forbids framing and sniffing. Nothing
   * at all when the folder is missing, so development (the Vite proxy) and the tests are unchanged.
   * Mount it after `/ws`: it answers every GET.
   */
  def routes(dist: Path): HttpRoutes[IO] =
    if !Files.isDirectory(dist) then HttpRoutes.empty[IO]
    else
      val files = fileService[IO](FileService.Config(dist.toString))
      HttpRoutes[IO] { request =>
        files(request).orElse(OptionT.pure[IO](Response[IO](Status.NotFound))).map(response =>
          response.putHeaders(hardening :+ caching(request, response))
        )
      }
