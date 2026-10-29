package dev.zaksael.rectangles.server.http

import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.net.http.HttpResponse.BodyHandlers
import java.nio.file.Files
import java.nio.file.Path

import scala.jdk.OptionConverters.*

import cats.effect.IO
import cats.syntax.semigroupk.*
import org.scalatest.EitherValues
import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.server.TestServer
import dev.zaksael.rectangles.server.WsTestClient

class StaticRoutesSpec extends AnyFlatSpec with Matchers with EitherValues with OptionValues:
  /** A built frontend in a temp folder, with a file beside it that must never be served. */
  private def withBuild[A](test: Path => A): A =
    val root = Files.createTempDirectory("static-routes")
    val dist = Files.createDirectory(root.resolve("dist"))
    Files.writeString(dist.resolve("index.html"), "<html><title>Rectangles</title></html>")
    Files.createDirectory(dist.resolve("assets"))
    Files.writeString(dist.resolve("assets").resolve("app.js"), "console.log(1)")
    Files.writeString(root.resolve("secret.txt"), "not for the web")
    test(dist)

  private def served[A](dist: Path)(test: Int => A): A =
    TestServer.use(ws => (WsRoutes.routes(ws) <+> StaticRoutes.routes(dist)).orNotFound)(test)

  private def get(port: Int, path: String): HttpResponse[String] =
    HttpClient
      .newHttpClient()
      .send(
        HttpRequest.newBuilder(URI.create(s"http://127.0.0.1:$port$path")).GET().build(),
        BodyHandlers.ofString(),
      )

  private def header(response: HttpResponse[String], name: String): Option[String] =
    response.headers.firstValue(name).toScala

  "the built frontend" should "be served at the root with its assets, and leave the websocket working" in
    withBuild { dist =>
      served(dist) { port =>
        val root  = get(port, "/")
        val asset = get(port, "/assets/app.js")
        root.statusCode shouldBe 200
        root.body should include("Rectangles")
        (asset.statusCode, asset.body) shouldBe (200, "console.log(1)")
        val client = WsTestClient.connect(port, "protocolVersion=1").value
        try client.next().hcursor.get[String]("type").value shouldBe "state"
        finally client.close()
      }
    }

  it should "forbid framing and sniffing on every response" in
    withBuild { dist =>
      served(dist) { port =>
        for path <- List("/", "/assets/app.js", "/nope") do
          withClue(path) {
            val response = get(port, path)
            header(response, "X-Frame-Options") shouldBe Some("DENY")
            header(response, "X-Content-Type-Options") shouldBe Some("nosniff")
          }
      }
    }

  it should "cache the hashed assets for good and make the page revalidate" in
    withBuild { dist =>
      served(dist) { port =>
        header(get(port, "/assets/app.js"), "Cache-Control") shouldBe
          Some("public, max-age=31536000, immutable")
        header(get(port, "/"), "Cache-Control") shouldBe Some("no-cache")
      }
    }

  it should "keep an asset cached when the browser revalidates it" in
    withBuild { dist =>
      served(dist) { port =>
        val etag = header(get(port, "/assets/app.js"), "ETag").value
        val revalidated = HttpClient
          .newHttpClient()
          .send(
            HttpRequest
              .newBuilder(URI.create(s"http://127.0.0.1:$port/assets/app.js"))
              .header("If-None-Match", etag)
              .GET()
              .build(),
            BodyHandlers.ofString(),
          )
        revalidated.statusCode shouldBe 304
        header(revalidated, "Cache-Control") shouldBe Some("public, max-age=31536000, immutable")
      }
    }

  it should "not cache a missing asset" in
    withBuild { dist =>
      served(dist) { port =>
        val missing = get(port, "/assets/gone.js")
        missing.statusCode shouldBe 404
        header(missing, "Cache-Control") shouldBe Some("no-cache")
      }
    }

  it should "answer an unknown path with 404" in
    withBuild { dist =>
      served(dist)(port => get(port, "/nope").statusCode shouldBe 404)
    }

  it should "not leave its folder" in
    withBuild { dist =>
      served(dist) { port =>
        for path <- List("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt") do
          withClue(path)(get(port, path).body should not include "not for the web")
      }
    }

  "a missing frontend folder" should "change nothing: 404 at the root and the websocket works" in
    withBuild { dist =>
      served(dist.resolve("no-such-dist")) { port =>
        get(port, "/").statusCode shouldBe 404
        val client = WsTestClient.connect(port, "protocolVersion=1").value
        try client.next().hcursor.get[String]("type").value shouldBe "state"
        finally client.close()
      }
    }
