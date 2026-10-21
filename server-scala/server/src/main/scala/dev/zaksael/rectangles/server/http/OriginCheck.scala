package dev.zaksael.rectangles.server.http

import org.http4s.Uri

object OriginCheck:
  /**
   * A browser always sends Origin on a WebSocket upgrade, so a page served from anywhere but this
   * host is refused; no Origin means a script or a test, which cross-site hijacking cannot use.
   */
  // shortcut: same host and port only, no allowlist; add one if a proxy that rewrites Host ever fronts the server.
  def allowed(origin: Option[String], host: Option[String]): Boolean =
    origin.forall(page =>
      Uri.fromString(page).toOption.flatMap(_.authority).map(_.renderString).exists(host.contains)
    )
