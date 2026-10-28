package dev.zaksael.rectangles.server

import scala.concurrent.duration.*

import cats.effect.IO
import fs2.Stream
import org.http4s.HttpRoutes
import org.http4s.dsl.io.*
import org.http4s.websocket.WebSocketFrame
import org.scalatest.EitherValues
import org.scalatest.exceptions.TestFailedException
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class WsTestClientSpec extends AnyFlatSpec with Matchers with EitherValues:
  /** A client on a server whose only message to it is `sends` (nothing when empty). */
  private def clientOf[A](sends: Option[String])(test: WsTestClient => A): A =
    TestServer.use(ws =>
      HttpRoutes.of[IO] { case GET -> Root / "ws" =>
        val out = sends.fold(Stream.never[IO])(text =>
          Stream.emit(WebSocketFrame.Text(text)) ++ Stream.never[IO]
        )
        ws.build(out, _.drain)
      }.orNotFound
    ) { port =>
      val client = WsTestClient.connect(port, "").value
      try test(client)
      finally client.close()
    }

  "WsTestClient.next" should "fail the test when the server sends nothing within the wait" in:
    clientOf(None) { client =>
      val failure = intercept[TestFailedException](client.next(200.millis))
      failure.getMessage.contains("no message") shouldBe true
    }

  it should "fail the test with the text when a message is not JSON" in:
    clientOf(Some("not json")) { client =>
      val failure = intercept[TestFailedException](client.next())
      failure.getMessage.contains("not json") shouldBe true
    }
