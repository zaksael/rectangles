package dev.zaksael.rectangles.server

import java.net.URI
import java.net.http.HttpClient
import java.net.http.WebSocket
import java.net.http.WebSocketHandshakeException
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CompletionStage
import java.util.concurrent.ExecutionException
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

import scala.concurrent.duration.*
import scala.util.Try

import cats.effect.IO
import com.comcast.ip4s.port
import io.circe.Json
import io.circe.parser
import org.http4s.HttpApp
import org.http4s.ember.server.EmberServerBuilder
import org.http4s.server.websocket.WebSocketBuilder2

/** A WebSocket client for tests: the messages it receives queue up, and the close code is kept. */
final class WsTestClient private (
    socket: WebSocket,
    inbox: LinkedBlockingQueue[String],
    closed: CompletableFuture[Int],
):
  def send(text: String): Unit = socket.sendText(text, true).get(5, TimeUnit.SECONDS): Unit

  /** The next message from the server, parsed; Json.Null after 5 seconds without one. */
  def next(): Json =
    Option(inbox.poll(
      5,
      TimeUnit.SECONDS,
    )).flatMap(text => parser.parse(text).toOption).getOrElse(Json.Null)

  /** The close code the server sent, or None when the connection is still open after 5 seconds. */
  def closeCode(): Option[Int] = Try(closed.get(5, TimeUnit.SECONDS)).toOption

  def close(): Unit =
    Try(socket.sendClose(WebSocket.NORMAL_CLOSURE, "").get(5, TimeUnit.SECONDS)): Unit

object WsTestClient:
  /**
   * Connects to `/ws?query` with the extra request headers; Left is the status of a refused
   * handshake.
   */
  def connect(
      port: Int,
      query: String,
      headers: Map[String, String] = Map.empty,
  ): Either[Int, WsTestClient] =
    val inbox   = new LinkedBlockingQueue[String]
    val closed  = new CompletableFuture[Int]
    val partial = new java.lang.StringBuilder
    val listener = new WebSocket.Listener:
      // A message can arrive in several pieces; it is queued once the last one is in.
      override def onText(ws: WebSocket, data: CharSequence, last: Boolean): CompletionStage[?] =
        partial.append(data)
        if last then
          inbox.add(partial.toString): Unit
          partial.setLength(0)
        ws.request(1)
        CompletableFuture.completedFuture(())
      override def onClose(ws: WebSocket, statusCode: Int, reason: String): CompletionStage[?] =
        closed.complete(statusCode): Unit
        CompletableFuture.completedFuture(())
      override def onError(ws: WebSocket, error: Throwable): Unit = closed.complete(1006): Unit
    val builder = headers.foldLeft(HttpClient.newHttpClient().newWebSocketBuilder())((b, h) =>
      b.header(h._1, h._2)
    )
    Try(builder.buildAsync(
      URI.create(s"ws://127.0.0.1:$port/ws?$query"),
      listener,
    ).get(5, TimeUnit.SECONDS)).toEither.left
      .map {
        case failed: ExecutionException =>
          failed.getCause match
            case refused: WebSocketHandshakeException => refused.getResponse.statusCode
            case _                                    => -1
        case _ => -1
      }
      .map(new WsTestClient(_, inbox, closed))

/** Ember on a free port serving `app` while `test` runs. */
object TestServer:
  def use[A](
      app: WebSocketBuilder2[IO] => HttpApp[IO],
      idleTimeout: Duration = 60.seconds,
  )(test: Int => A): A =
    import cats.effect.unsafe.implicits.global
    EmberServerBuilder
      .default[IO]
      .withPort(port"0")
      .withIdleTimeout(idleTimeout)
      .withHttpWebSocketApp(app)
      .build
      .use(server => IO.blocking(test(server.address.getPort)))
      .unsafeRunSync()
