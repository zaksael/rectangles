package dev.zaksael.rectangles.server

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.net.http.HttpResponse.BodyHandlers
import java.net.http.WebSocket
import java.util.concurrent.CompletableFuture
import java.util.concurrent.CompletionStage
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

import scala.annotation.tailrec
import scala.concurrent.duration.*
import scala.util.Try

import cats.effect.IO
import io.circe.Json
import io.circe.parser.parse
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.server.http.WsRoutes
import dev.zaksael.rectangles.server.session.Connect
import dev.zaksael.rectangles.server.session.GameSession
import dev.zaksael.rectangles.server.session.Play
import dev.zaksael.rectangles.server.session.Session

class WsRoutesSpec extends AnyFlatSpec with Matchers with EitherValues:
  private val vanilla = "protocolVersion=1"

  /** Player One starts, as the scripted wire cases expect (the real route flips a coin). */
  private val playerOneStarts: Connect => IO[Session] = connect =>
    GameSession.create(
      Play(GameState.initial(connect.rules, PlayerId.One), SplitMix64(42L)),
      connect.bot,
    )

  /** A client on a fresh game, closed when `test` ends so the server can shut down at once. */
  private def connected[A](query: String = vanilla)(test: WsTestClient => A): A =
    TestServer.use(ws => WsRoutes.routes(ws, playerOneStarts).orNotFound) { port =>
      val client = WsTestClient.connect(port, query).value
      try test(client)
      finally client.close()
    }

  "a client that connects" should "get the opening state of a new game" in
    connected() { client =>
      val message = client.next()
      message.hcursor.get[String]("type").value shouldBe "state"
      message.hcursor.get[Json]("series").value shouldBe Json.Null
      val turn = message.hcursor.downField("game").downField("turn")
      turn.get[String]("turnState").value shouldBe "awaitingRoll"
      turn.get[Json]("lastRoll").value shouldBe Json.Null
    }

  private def say(client: WsTestClient, text: String): Json =
    client.send(text)
    client.next()

  private def action(kind: String) = s"""{"protocolVersion":1,"type":"$kind"}"""

  private def reason(message: Json): String = message.hcursor.get[String]("reason").value

  private def turn(message: Json) = message.hcursor.downField("game").downField("turn")

  /** Rolls, then places the first legal spot of the roll; returns the state after the placement. */
  private def rollAndPlace(client: WsTestClient): Json =
    val legal           = turn(say(client, action("roll"))).downField("legalPlacements").downArray
    val spot            = legal.downField("topLefts").downArray
    val (row, col)      = (spot.downN(0).as[Int].value, spot.downN(1).as[Int].value)
    val (width, height) = (legal.get[Int]("width").value, legal.get[Int]("height").value)
    say(
      client,
      s"""{"protocolVersion":1,"type":"place","topLeft":[$row,$col],"width":$width,"height":$height}""",
    )

  "a client playing the bot" should "get the human's move, then the bot's roll and its move as separate states" in
    connected(s"$vanilla&botSeats=2") { client =>
      client.next()
      val afterHuman = rollAndPlace(client)
      turn(afterHuman).get[Int]("currentPlayerId").value shouldBe 2
      turn(afterHuman).get[String]("turnState").value shouldBe "awaitingRoll"

      val afterRoll = client.next()
      turn(afterRoll).get[Int]("currentPlayerId").value shouldBe 2
      turn(afterRoll).get[Json]("lastRoll").value should not be Json.Null

      val afterMove = client.next()
      turn(afterMove).get[Int]("currentPlayerId").value shouldBe 1
      turn(afterMove).get[String]("turnState").value shouldBe "awaitingRoll"
      afterMove.hcursor.downField("game").downField("players").downField("2").downField(
        "board"
      ).get[List[Json]]("pieces").value should have size 1
    }

  "a client that connects with walls on" should "get a game with wall edges" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&wallsEnabled=true").value
      try
        val walls =
          client.next().hcursor.downField("game").downField("houseRules").downField("walls")
        walls.get[Boolean]("enabled").value shouldBe true
        walls.get[List[Json]]("edges").value should not be empty
      finally client.close()
    }

  "a client that connects with obstacles on" should "get a game with obstacle cells" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&obstaclesEnabled=true").value
      try
        val obstacles =
          client.next().hcursor.downField("game").downField("houseRules").downField("obstacles")
        obstacles.get[Boolean]("enabled").value shouldBe true
        obstacles.get[List[Json]]("cells").value should not be empty
      finally client.close()
    }

  "a client that connects with prizes on" should "get a game with prize cells" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&prizeEnabled=true").value
      try
        val prize =
          client.next().hcursor.downField("game").downField("houseRules").downField("prize")
        prize.get[Boolean]("enabled").value shouldBe true
        prize.get[List[Json]]("cells").value should not be empty
      finally client.close()
    }

  "a client that connects with pitfalls on" should "get a game with pitfall cells" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&pitfallEnabled=true").value
      try
        val pitfall =
          client.next().hcursor.downField("game").downField("houseRules").downField("pitfall")
        pitfall.get[Boolean]("enabled").value shouldBe true
        pitfall.get[List[Json]]("cells").value should not be empty
      finally client.close()
    }

  "a client that connects with steal cells on" should "get a game with steal cells" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&stealEnabled=true").value
      try
        val steal =
          client.next().hcursor.downField("game").downField("houseRules").downField("steal")
        steal.get[Boolean]("enabled").value shouldBe true
        steal.get[List[Json]]("cells").value should not be empty
      finally client.close()
    }

  "a client that connects with the self-enclosed penalty on" should "get a game with the rule enabled" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&selfEnclosedPenaltyEnabled=true").value
      try
        val rule = client.next().hcursor.downField("game").downField("houseRules")
          .downField("selfEnclosedPenalty")
        rule.get[Boolean]("enabled").value shouldBe true
      finally client.close()
    }

  "a client that connects with rerolls on" should "get a game where a reroll can be spent" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&rerollEnabled=true").value
      try
        val reroll =
          client.next().hcursor.downField("game").downField("houseRules").downField("reroll")
        reroll.get[Boolean]("enabled").value shouldBe true
        reroll.get[Boolean]("canReroll").value shouldBe true
      finally client.close()
    }

  "a client that connects with the comeback nudge on" should "get a game with the rule enabled" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&comebackNudgeEnabled=true").value
      try
        val rule =
          client.next().hcursor.downField("game").downField("houseRules").downField("comebackNudge")
        rule.get[Boolean]("enabled").value shouldBe true
      finally client.close()
    }

  "a client that connects with the wildcard on" should "get a game with the rule enabled" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      val client = WsTestClient.connect(port, s"$vanilla&wildcardEnabled=true").value
      try
        val wildcard =
          client.next().hcursor.downField("game").downField("houseRules").downField("wildcard")
        wildcard.get[Boolean]("enabled").value shouldBe true
        say(client, """{"protocolVersion":1,"type":"chooseWildcard","value":4}""")
          .hcursor.get[String]("reason").value shouldBe "invalidAction"
      finally client.close()
    }

  "a roll" should "answer with a state that holds the roll" in
    connected() { client =>
      client.next()
      val rolled = say(client, action("roll"))
      rolled.hcursor.get[String]("type").value shouldBe "state"
      turn(rolled).get[Json]("lastRoll").value should not be Json.Null
      turn(rolled).get[String]("turnState").value should not be "awaitingRoll"
    }

  it should "be refused as an invalid action when the turn is already rolled, and the connection stays open" in
    connected() { client =>
      client.next()
      say(client, action("roll"))
      reason(say(client, action("roll"))) shouldBe "invalidAction"
      reason(say(client, action("roll"))) shouldBe "invalidAction"
    }

  "a placement" should "pass the turn to a human Player Two and record the piece" in
    connected() { client =>
      client.next()
      val placed = rollAndPlace(client)
      turn(placed).get[Int]("currentPlayerId").value shouldBe 2
      turn(placed).get[String]("turnState").value shouldBe "awaitingRoll"
      turn(placed).get[Json]("lastRoll").value shouldBe Json.Null
      placed.hcursor.downField("game").downField(
        "players"
      ).downField("1").downField("board").get[List[Json]]("pieces").value.size shouldBe 1
    }

  it should "be refused as illegal at a spot that is not anchored to the start corner" in
    connected() { client =>
      client.next()
      say(client, action("roll"))
      reason(say(
        client,
        """{"protocolVersion":1,"type":"place","topLeft":[18,18],"width":1,"height":1}""",
      )) shouldBe "illegalPlacement"
    }

  it should "be refused as illegal before any roll" in
    connected() { client =>
      client.next()
      reason(say(
        client,
        """{"protocolVersion":1,"type":"place","topLeft":[0,0],"width":1,"height":1}""",
      )) shouldBe "illegalPlacement"
    }

  "a skip before any roll" should "be refused as an invalid action" in
    connected() { client =>
      client.next()
      reason(say(client, action("skip"))) shouldBe "invalidAction"
    }

  "a surrender" should "end the game and declare the opponent the winner" in
    connected() { client =>
      client.next()
      val over = say(client, action("surrender")).hcursor.downField("game")
      over.downField("turn").get[String]("turnState").value shouldBe "gameOver"
      over.downField("gameOver").get[String]("reason").value shouldBe "surrender"
      over.downField("gameOver").get[Int]("playerId").value shouldBe 1
      over.downField("gameOver").get[Int]("winner").value shouldBe 2
    }

  it should "change nothing the second time" in
    connected() { client =>
      client.next()
      say(client, action("surrender"))
      val again = say(client, action("surrender"))
      again.hcursor.get[String]("type").value shouldBe "state"
      again.hcursor.downField(
        "game"
      ).downField("gameOver").get[String]("reason").value shouldBe "surrender"
    }

  "text that is not a message, or a message of another version" should "get an error and keep the connection open" in
    connected() { client =>
      client.next()
      reason(say(client, "not json")) shouldBe "malformedMessage"
      reason(say(client, """{"protocolVersion":1}""")) shouldBe "malformedMessage"
      reason(say(
        client,
        """{"protocolVersion":2,"type":"roll"}""",
      )) shouldBe "protocolVersionMismatch"
      reason(say(
        client,
        """{"protocolVersion":2,"type":"roll"}""",
      )) shouldBe "protocolVersionMismatch"
      say(client, action("roll")).hcursor.get[String]("type").value shouldBe "state"
    }

  "a connect the server refuses" should "get HTTP 403 for parameters it does not know or a page from another host" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      WsTestClient.connect(port, "protocolVersion=1&boardSize=20").left.value shouldBe 403
      WsTestClient.connect(port, "").left.value shouldBe 403
      WsTestClient.connect(
        port,
        vanilla,
        Map("Origin" -> "http://evil.example"),
      ).left.value shouldBe 403
    }

  it should "get HTTP 403 for a parameter given twice, even with the same value" in
    TestServer.use(ws => WsRoutes.routes(ws).orNotFound) { port =>
      WsTestClient.connect(
        port,
        "protocolVersion=1&boardSize=19&boardSize=23",
      ).left.value shouldBe 403
      WsTestClient.connect(
        port,
        "protocolVersion=1&boardSize=19&boardSize=19",
      ).left.value shouldBe 403
    }

  "a bug in the game" should "close the connection instead of becoming an error message" in {
    val failing = new Session:
      def state: IO[Vector[Json]] =
        IO.pure(Vector(parse("""{"protocolVersion":1,"type":"state"}""").value))
      def handle(text: String): IO[Vector[Json]] = IO.raiseError(new RuntimeException("boom"))
    TestServer.use(ws => WsRoutes.routes(ws, _ => IO.pure(failing)).orNotFound) { port =>
      val client = WsTestClient.connect(port, vanilla).value
      client.next()
      client.send(action("roll"))
      client.closeCode() should not be None
    }
  }

  "a connection that stays quiet" should "stay open, because the server pings it before the idle timeout" in
    TestServer.use(
      ws => WsRoutes.routes(ws, playerOneStarts, keepAlive = 300.millis).orNotFound,
      idleTimeout = 2.seconds,
    ) { port =>
      val client = WsTestClient.connect(port, vanilla).value
      try
        client.next()
        Thread.sleep(3000)
        say(client, action("roll")).hcursor.get[String]("type").value shouldBe "state"
      finally client.close()
    }

  "a message far larger than any real one" should "close the connection (Ember drops it past its fragment limit)" in
    connected() { client =>
      client.next()
      Try(client.send("x" * 20000000))
      client.closeCode() should not be None
    }

  "a client that sends but never reads" should "stop the server taking its messages once the outbox is full" in {
    val handled = new AtomicInteger
    val big     = Json.fromString("x" * 262144)
    val sessions: Connect => IO[Session] = _ =>
      IO.pure(new Session:
        def state: IO[Vector[Json]] = IO.pure(Vector(Json.obj()))
        def handle(text: String): IO[Vector[Json]] =
          IO.delay(handled.incrementAndGet()).as(Vector(big)))
    // A listener that asks for no message after the first, so the replies pile up on the server.
    val silent = new WebSocket.Listener:
      override def onText(ws: WebSocket, data: CharSequence, last: Boolean): CompletionStage[?] =
        CompletableFuture.completedFuture(())
    @tailrec def settled(previous: Int, stableFor: Int): Int =
      Thread.sleep(250)
      val now = handled.get
      if now == previous && stableFor >= 4 then now
      else settled(now, if now == previous then stableFor + 1 else 0)
    TestServer.use(ws => WsRoutes.routes(ws, sessions).orNotFound) { port =>
      val socket = HttpClient
        .newHttpClient()
        .newWebSocketBuilder()
        .buildAsync(URI.create(s"ws://localhost:$port/ws?$vanilla"), silent)
        .get(5, TimeUnit.SECONDS)
      try
        (1 to 300).foreach(_ => socket.sendText("{}", true).get(5, TimeUnit.SECONDS))
        settled(-1, 0) should be < 150
      finally socket.abort()
    }
  }

  "a message just over 64 KiB" should "close the connection" in
    connected() { client =>
      client.next()
      Try(client.send("x" * 65537))
      client.closeCode() should not be None
    }

  private def httpGet(port: Int, path: String): HttpResponse[String] =
    HttpClient
      .newHttpClient()
      .send(
        HttpRequest.newBuilder(URI.create(s"http://127.0.0.1:$port$path")).GET().build(),
        BodyHandlers.ofString(),
      )

  "other requests" should "get 404 for an unknown path, with no CORS headers" in
    TestServer.use(ws => WsRoutes.routes(ws, playerOneStarts).orNotFound) { port =>
      val response = httpGet(port, "/nope")
      response.statusCode shouldBe 404
      response.headers.firstValue("Access-Control-Allow-Origin").isPresent shouldBe false
    }

  it should "refuse a plain GET of /ws that does not ask for a WebSocket" in
    TestServer.use(ws => WsRoutes.routes(ws, playerOneStarts).orNotFound) { port =>
      httpGet(port, s"/ws?$vanilla").statusCode should (be >= 400 and be < 500)
    }
