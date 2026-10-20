package dev.zaksael.rectangles.server

import cats.effect.IO
import cats.effect.unsafe.implicits.global
import org.http4s.Request
import org.http4s.Status
import org.http4s.implicits.*
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.server.http.HealthRoutes

class HealthRoutesSpec extends AnyFlatSpec with Matchers:
  "the health route" should "answer GET /health with 200 and ok" in {
    val response =
      HealthRoutes.routes.orNotFound.run(Request[IO](uri = uri"/health")).unsafeRunSync()
    response.status shouldBe Status.Ok
    response.as[String].unsafeRunSync() shouldBe "ok"
  }

  it should "not answer other paths" in {
    val response = HealthRoutes.routes.orNotFound.run(Request[IO](uri = uri"/nope")).unsafeRunSync()
    response.status shouldBe Status.NotFound
  }
