package dev.zaksael.rectangles.server.http

import java.util.concurrent.atomic.AtomicInteger

import scala.concurrent.duration.*

import cats.effect.IO
import cats.effect.std.Queue
import cats.effect.std.SecureRandom
import cats.syntax.foldable.*
import fs2.Stream
import io.circe.Json
import logging4s.cats.CatsInstances.given
import logging4s.console.ConsoleInstances.given
import logging4s.core.Logging
import logging4s.core.syntax.loggable.*
import org.http4s.HttpRoutes
import org.http4s.dsl.io.*
import org.http4s.server.websocket.WebSocketBuilder2
import org.http4s.websocket.WebSocketFrame
import org.typelevel.ci.CIString

import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.server.session.Connect
import dev.zaksael.rectangles.server.session.ConnectParams
import dev.zaksael.rectangles.server.session.GameSession
import dev.zaksael.rectangles.server.session.Session

object WsRoutes:
  /** A new game for what the connect asks for, its dice seeded from real entropy. */
  val newGame: Connect => IO[Session] = connect =>
    for
      random <- SecureRandom.javaSecuritySecureRandom[IO]
      seed   <- random.nextLong
      session <-
        GameSession.create(ConnectParams.open(connect, SplitMix64(seed)), connect.bot)
    yield session

  /** The longest text a client may send, in bytes. */
  val maxMessageSize: Int = 64 * 1024

  /**
   * Replies a connection may have waiting; a client that reads slower than it sends is held back
   * past it.
   */
  private val outboxSize = 64

  /** Connections open right now, across the whole process; only the log lines read it. */
  private val openConnections = new AtomicInteger

  private def send(outbox: Queue[IO, Option[WebSocketFrame]], message: Json): IO[Unit] =
    outbox.offer(Some(WebSocketFrame.Text(message.noSpaces)))

  /**
   * `GET /ws`: refuses (403) a page from another host, parameters it does not know or a parameter
   * given twice; otherwise sends the opening state and answers each client text with the reply the
   * session gives.
   */
  def routes(
      ws: WebSocketBuilder2[IO],
      sessions: Connect => IO[Session] = newGame,
      keepAlive: FiniteDuration = 20.seconds,
  ): HttpRoutes[IO] =
    HttpRoutes.of[IO] { case req @ GET -> Root / "ws" =>
      def header(name: String) = req.headers.get(CIString(name)).map(_.head.value)
      val keys                 = req.uri.query.pairs.map(_._1)
      def refuse(reason: String) =
        Logging.create[IO]("WsRoutes").flatMap(
          _.warn("connect refused", reason.asLogValue("reason"))
        ) *> Forbidden()
      ConnectParams.parse(req.uri.query.params) match
        case None                                       => refuse("badParameters")
        case Some(_) if keys.distinct.size != keys.size => refuse("repeatedParameter")
        case Some(_) if !OriginCheck.allowed(header("Origin"), header("Host")) =>
          refuse("badOrigin")
        case Some(connect) =>
          for
            log     <- Logging.create[IO]("WsRoutes")
            session <- sessions(connect)
            outbox  <- Queue.bounded[IO, Option[WebSocketFrame]](outboxSize)
            opening <- session.state
            _       <- opening.traverse_(message => send(outbox, message))
            _ <- IO.delay(openConnections.incrementAndGet()).flatMap(open =>
              log.info("connection opened", open.asLogValue("open"))
            )
            socket <- ws.build(
              Stream
                .fromQueueNoneTerminated(outbox)
                .mergeHaltL(Stream.awakeEvery[IO](keepAlive).as(WebSocketFrame.Ping())),
              _.evalMap {
                case WebSocketFrame.Text(text, _) =>
                  session.handle(text).flatMap(_.traverse_(message => send(outbox, message)))
                case _ => IO.unit
              }.onFinalize(
                outbox.tryOffer(None).void *>
                  IO.delay(openConnections.decrementAndGet()).flatMap(open =>
                    log.info("connection closed", open.asLogValue("open"))
                  )
              ),
            )
          yield socket
    }
