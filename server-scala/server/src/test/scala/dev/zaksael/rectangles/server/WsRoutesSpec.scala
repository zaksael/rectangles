package dev.zaksael.rectangles.server

import java.net.URI
import java.net.http.HttpClient
import java.net.http.WebSocket
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CompletionStage
import java.util.concurrent.TimeUnit

import cats.effect.IO
import cats.effect.unsafe.implicits.global
import com.comcast.ip4s.port
import org.http4s.ember.server.EmberServerBuilder
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.server.http.WsRoutes

class WsRoutesSpec extends AnyFlatSpec with Matchers:
  /**
   * The first text message a client receives after connecting; fails after 5 seconds if there is
   * none.
   */
  private def firstMessage(port: Int): String =
    val received = new CompletableFuture[String]
    val listener = new WebSocket.Listener:
      override def onText(ws: WebSocket, data: CharSequence, last: Boolean): CompletionStage[?] =
        received.complete(data.toString)
        CompletableFuture.completedFuture(())
    HttpClient
      .newHttpClient()
      .newWebSocketBuilder()
      .buildAsync(URI.create(s"ws://127.0.0.1:$port/ws?protocolVersion=1"), listener)
      .get(5, TimeUnit.SECONDS)
    received.get(5, TimeUnit.SECONDS)

  "the /ws stub" should "send a state message when a client connects" in {
    val message = EmberServerBuilder
      .default[IO]
      .withPort(port"0")
      .withHttpWebSocketApp(ws => WsRoutes.routes(ws).orNotFound)
      .build
      .use(server => IO.blocking(firstMessage(server.address.getPort)))
      .unsafeRunSync()
    message shouldBe """{"protocolVersion":1,"type":"state"}"""
  }
