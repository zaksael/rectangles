package dev.zaksael.rectangles.server.http

import scala.concurrent.duration.*

import cats.effect.IO
import cats.effect.std.Queue
import cats.effect.std.SecureRandom
import fs2.Stream
import org.http4s.HttpRoutes
import org.http4s.dsl.io.*
import org.http4s.server.websocket.WebSocketBuilder2
import org.http4s.websocket.WebSocketFrame
import org.typelevel.ci.CIString

import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.server.session.ConnectParams
import dev.zaksael.rectangles.server.session.GameSession
import dev.zaksael.rectangles.server.session.Session

object WsRoutes:
  /** A new game for the rules, its dice seeded from real entropy. */
  val newGame: Rules => IO[Session] = rules =>
    for
      random  <- SecureRandom.javaSecuritySecureRandom[IO]
      seed    <- random.nextLong
      session <- GameSession.create(ConnectParams.start(rules, SplitMix64(seed)))
    yield session

  /**
   * `GET /ws`: refuses (403) a page from another host or parameters it does not know; otherwise
   * sends the opening state and answers each client text with the reply the session gives.
   */
  def routes(
      ws: WebSocketBuilder2[IO],
      sessions: Rules => IO[Session] = newGame,
      keepAlive: FiniteDuration = 20.seconds,
  ): HttpRoutes[IO] =
    HttpRoutes.of[IO] { case req @ GET -> Root / "ws" =>
      def header(name: String) = req.headers.get(CIString(name)).map(_.head.value)
      ConnectParams.parse(req.uri.query.params) match
        case Some(rules) if OriginCheck.allowed(header("Origin"), header("Host")) =>
          for
            session <- sessions(rules)
            outbox  <- Queue.unbounded[IO, Option[WebSocketFrame]]
            opening <- session.state
            _       <- outbox.offer(Some(WebSocketFrame.Text(opening.noSpaces)))
            socket <- ws.build(
              Stream
                .fromQueueNoneTerminated(outbox)
                .mergeHaltL(Stream.awakeEvery[IO](keepAlive).as(WebSocketFrame.Ping())),
              _.evalMap {
                case WebSocketFrame.Text(text, _) =>
                  session.handle(text).flatMap(reply =>
                    outbox.offer(Some(WebSocketFrame.Text(reply.noSpaces)))
                  )
                case _ => IO.unit
              }.onFinalize(outbox.offer(None)),
            )
          yield socket
        case _ => Forbidden()
    }
