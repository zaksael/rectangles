package dev.zaksael.rectangles.server

import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Path

import scala.io.Source
import scala.util.Using

import io.circe.Decoder
import io.circe.HCursor
import io.circe.Json
import io.circe.parser

/**
 * A random draw the Python reference made: replaying them in order reproduces the recorded game.
 */
enum Draw:
  case RandInt(lo: Int, hi: Int, value: Int)
  case Choice(size: Int, index: Int)

/** One client message (None for the connect) and every reply it produced. */
final case class Step(send: Option[Json], receive: Vector[Json])

/** A recorded session: the connect params, the draws the game consumed, and the wire traffic. */
final case class GoldenGame(
    name: String,
    connect: Map[String, String],
    pinnedStarter: Boolean,
    draws: Vector[Draw],
    steps: Vector[Step],
)

object Golden:
  /** Where the fixtures live, relative to the sbt build root (`server-scala/`). */
  val dir: Path = Path.of("server/src/test/resources/golden")

  private given Decoder[Draw] = Decoder.instance { c =>
    c.as[Vector[Json]].flatMap {
      case Vector(kind, lo, hi, value) if kind.asString.contains("randint") =>
        for
          l <- lo.as[Int]
          h <- hi.as[Int]
          v <- value.as[Int]
        yield Draw.RandInt(l, h, v)
      case Vector(kind, size, index) if kind.asString.contains("choice") =>
        for
          s <- size.as[Int]
          i <- index.as[Int]
        yield Draw.Choice(s, i)
      case other => Left(io.circe.DecodingFailure(s"not a draw: $other", c.history))
    }
  }

  private given Decoder[Step] = Decoder.instance { c =>
    for
      send    <- c.get[Option[Json]]("send")
      receive <- c.get[Vector[Json]]("receive")
    yield Step(send, receive)
  }

  private given Decoder[GoldenGame] = Decoder.instance { (c: HCursor) =>
    for
      name    <- c.get[String]("name")
      connect <- c.get[Map[String, Json]]("connect")
      pinned  <- c.get[Boolean]("pinnedStarter")
      draws   <- c.get[Vector[Draw]]("draws")
      steps   <- c.get[Vector[Step]]("steps")
    yield GoldenGame(
      name,
      connect.view.mapValues(v => v.asString.getOrElse(v.noSpaces)).toMap,
      pinned,
      draws,
      steps,
    )
  }

  /** Loads the fixture `name` from the test resources. */
  def load(name: String): Either[String, GoldenGame] =
    Using(
      Source.fromResource(s"golden/$name.json")(using scala.io.Codec.UTF8)
    )(_.mkString).toEither.left
      .map(_.toString)
      .flatMap(text => parser.decode[GoldenGame](text).left.map(_.toString))

  /**
   * Rewrites the fixture when `enabled` (the `UPDATE_GOLDEN=1` mode, used only after the Python
   * reference is gone). Returns whether it wrote.
   */
  def update(
      name: String,
      content: String,
      target: Path = dir,
      enabled: Boolean = sys.env.get("UPDATE_GOLDEN").contains("1"),
  ): Boolean =
    if enabled then
      Files.writeString(target.resolve(s"$name.json"), content, StandardCharsets.UTF_8)
      true
    else false
