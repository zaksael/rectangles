package dev.zaksael.rectangles.server

import dev.zaksael.rectangles.rules.Dice

/**
 * Dice that hand back the recorded draws in order; a draw asked for with another range is noted in
 * `problems`.
 */
final case class ReplayDice(draws: List[Draw], problems: List[String] = Nil) extends Dice:
  def between(lo: Int, hi: Int): (Int, Dice) = draws match
    case Draw.RandInt(`lo`, `hi`, value) :: rest => (value, copy(draws = rest))
    case Draw.Choice(size, index) :: rest if lo == 0 && hi == size - 1 =>
      (index, copy(draws = rest))
    case other :: rest => (lo, ReplayDice(rest, problems :+ s"asked for $lo..$hi, recorded $other"))
    case Nil           => (lo, copy(problems = problems :+ s"asked for $lo..$hi, nothing recorded"))
