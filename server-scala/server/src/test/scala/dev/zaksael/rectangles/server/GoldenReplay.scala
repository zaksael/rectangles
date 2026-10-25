package dev.zaksael.rectangles.server

import java.util.concurrent.atomic.AtomicReference

import cats.effect.unsafe.implicits.global
import io.circe.Json

import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.Setup
import dev.zaksael.rectangles.server.session.ConnectParams
import dev.zaksael.rectangles.server.session.GameSession
import dev.zaksael.rectangles.server.session.Play

/**
 * Dice that note where the recorded draws stand after every draw, so a replay can read the rest.
 */
final private class RecordingDice(inner: ReplayDice, seen: AtomicReference[ReplayDice])
    extends Dice:
  def between(lo: Int, hi: Int): (Int, Dice) =
    val (value, next) = inner.between(lo, hi)
    seen.set(next)
    (value, RecordingDice(next, seen))

object GoldenReplay:
  /**
   * The differences between replaying `game` through a real `GameSession` and its recording; empty
   * when they match. A step listed in `pending` (with the task that will answer it) is not sent.
   */
  def run(game: GoldenGame, pending: Map[Int, String] = Map.empty): List[String] =
    ConnectParams.parse(game.connect).fold(List("connect refused")) { connect =>
      val replay    = ReplayDice(game.draws.toList)
      val seen      = AtomicReference(replay)
      val recording = RecordingDice(replay, seen)
      val play =
        if connect.seriesLength.isDefined then ConnectParams.open(connect, recording)
        else
          val (state, dice) =
            Setup.newGame(connect.rules, Option.when(game.pinnedStarter)(PlayerId.One), recording)
          Play(state, dice)
      val session = GameSession.create(play).unsafeRunSync()
      val replies = game.steps.zipWithIndex.flatMap { case (step, index) =>
        Option.unless(pending.contains(index)) {
          val reply = step.send.fold(session.state)(sent =>
            session.handle(sent.asString.getOrElse(sent.noSpaces))
          ).unsafeRunSync()
          compare(step.receive, reply).map(difference => s"step $index $difference")
        }
      }.flatten.toList
      val left = seen.get
      // A held-back step leaves its draws unused.
      replies ++ Option.when(pending.isEmpty && left.draws.nonEmpty)(
        s"${left.draws.size} recorded draws unused"
      ) ++
        left.problems
    }

  /** An error reply is compared on type and reason only: its message embeds Python enum names. */
  private def compare(expected: Vector[Json], actual: Vector[Json]): List[String] =
    (expected, actual) match
      case (Vector(want), Vector(got)) if want.hcursor.get[String]("type").contains("error") =>
        List("type", "reason").flatMap { key =>
          JsonDiff.diff(
            want.hcursor.get[Json](key).getOrElse(Json.Null),
            got.hcursor.get[Json](key).getOrElse(Json.Null),
            s"$$.$key",
          )
        }
      case (Vector(want), Vector(got)) => JsonDiff.diff(want, got)
      case _ => List(s"recorded ${expected.size} replies, the session gave ${actual.size}")
