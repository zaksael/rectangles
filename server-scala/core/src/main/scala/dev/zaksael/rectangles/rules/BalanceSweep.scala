package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.Seats

/** Two difficulties set against each other; the first one swaps seats from game to game. */
final case class Pairing(first: BotDifficulty, second: BotDifficulty)

/** One game of a pairing: the seat the first difficulty played, and how it ended. */
final case class PairingGame(firstSeat: PlayerId, result: MatchResult)

object BalanceSweep:
  /** Every first and second difficulty, a difficulty against itself included. */
  val pairings: Vector[Pairing] =
    for
      first  <- BotDifficulty.values.toVector
      second <- BotDifficulty.values.toVector
    yield Pairing(first, second)

  private val Header =
    "pairing (first/second)    games  first  second  ties  seat-One  margin  fill  end reasons"

  /**
   * A header and one row per pairing: wins for each difficulty, ties, seat One wins, mean margin of
   * decided games, mean fill, end reasons.
   */
  def report(rows: Vector[(Pairing, Vector[PairingGame])]): String =
    (Header +: rows.map(row)).mkString("\n")

  private def row(entry: (Pairing, Vector[PairingGame])): String =
    val (pairing, games)                         = entry
    def count(wins: PairingGame => Boolean): Int = games.count(wins)
    val decided                                  = games.filter(_.result.winner.isDefined)
    val margins = decided.map(g => math.abs(g.result.scores.one - g.result.scores.two).toDouble)
    val reasons = games
      .groupBy(g => g.result.reason.toString.takeWhile(_ != '('))
      .toVector
      .sortBy(_._1)
      .map((name, group) => s"$name=${group.size}")
      .mkString(",")
    "%-24s %6d %6d %7d %5d %9d %7.1f %5.2f  %s".formatLocal(
      java.util.Locale.ROOT,
      s"${pairing.first}/${pairing.second}",
      games.size,
      count(g => g.result.winner.contains(g.firstSeat)),
      count(g => g.result.winner.exists(_ != g.firstSeat)),
      count(_.result.winner.isEmpty),
      count(_.result.winner.contains(PlayerId.One)),
      mean(margins),
      mean(games.map(_.result.fill)),
      reasons,
    )

  private def mean(values: Vector[Double]): Double =
    if values.isEmpty then 0.0 else values.sum / values.size

  /**
   * `games` games of one pairing, game i drawn from `seed + i`. The first difficulty starts in seat
   * One on even games and sits in seat Two on odd ones; seat One always moves first, so each
   * difficulty gets the same number of first moves. A game where a bot has no move is left out.
   */
  def play(rules: Rules, pairing: Pairing, games: Int, seed: Long): Vector[PairingGame] =
    (0 until games).toVector.flatMap { i =>
      val firstSeat = if i % 2 == 0 then PlayerId.One else PlayerId.Two
      val seats     = Seats(pairing.second, pairing.second).updated(firstSeat, pairing.first)
      BotMatch
        .play(rules, seats, Some(PlayerId.One), SplitMix64(seed + i))
        .map(PairingGame(firstSeat, _))
    }

/**
 * Every pairing on default rules, one table on stdout. Run it with the full class name:
 * `sbt "core/runMain dev.zaksael.rectangles.rules.runBalanceSweep [games] [boardSize] [seed]"`.
 */
@main def runBalanceSweep(games: Int = 100, boardSize: Int = 19, seed: Long = 1L): Unit =
  val rules = Rules(boardSize = boardSize)
  println(BalanceSweep.report(BalanceSweep.pairings.map(p =>
    p -> BalanceSweep.play(rules, p, games, seed)
  )))
