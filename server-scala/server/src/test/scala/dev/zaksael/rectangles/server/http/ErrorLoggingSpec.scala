package dev.zaksael.rectangles.server.http

import scala.collection.mutable.ListBuffer

import cats.effect.IO
import cats.effect.unsafe.implicits.global
import org.http4s.HttpApp
import org.http4s.Request
import org.http4s.Response
import org.http4s.Status
import org.http4s.Uri
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

class ErrorLoggingSpec extends AnyFlatSpec with Matchers:
  /**
   * Runs `GET /x` through `app` wrapped in ErrorLogging; returns what the wrapped app gave and what
   * was logged.
   */
  private def run(app: HttpApp[IO]): (Either[Throwable, Response[IO]], List[(String, String)]) =
    val logged = ListBuffer.empty[(String, String)]
    val result = ErrorLogging(app, (request, problem) => IO(logged += ((request, problem))).void)
      .run(Request[IO](uri = Uri.unsafeFromString("/x")))
      .attempt
      .unsafeRunSync()
    (result, logged.toList)

  "a request that throws" should "be logged with its request line, and still fail" in {
    val (result, logged) = run(HttpApp[IO](_ => IO.raiseError(new RuntimeException("boom"))))
    result.isLeft shouldBe true
    logged.map(_._1) shouldBe List("GET /x")
    logged.map(_._2).mkString should include("boom")
  }

  "a request answered with a 500" should "be logged with its request line" in {
    val (result, logged) = run(HttpApp[IO](_ => IO.pure(Response[IO](Status.InternalServerError))))
    result.map(_.status) shouldBe Right(Status.InternalServerError)
    logged.map(_._1) shouldBe List("GET /x")
  }

  "a request answered with a 200" should "not be logged" in {
    val (_, logged) = run(HttpApp[IO](_ => IO.pure(Response[IO](Status.Ok))))
    logged shouldBe Nil
  }
