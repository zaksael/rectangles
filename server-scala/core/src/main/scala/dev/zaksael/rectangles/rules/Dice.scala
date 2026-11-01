package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Constants

/** A source of dice: every draw returns the value and the dice to draw the next one from. */
trait Dice:
  /**
   * A value in `lo` to `hi`, both included; the caller keeps `lo <= hi`, so the public draws below
   * are the way in.
   */
  private[rectangles] def between(lo: Int, hi: Int): (Int, Dice)

  /** One die, from the smallest to the largest face. */
  def die: (Int, Dice) = between(Constants.DICE_MIN, Constants.DICE_MAX)

  /** 0 or 1, each equally likely. */
  def coin: (Int, Dice) = between(0, 1)

  /** One of the options, each equally likely: never empty, so it always draws. */
  def chooseAmong[A](first: A, rest: A*): (A, Dice) =
    val options       = first +: rest
    val (index, next) = between(0, options.size - 1)
    (options(index), next)

  /** One of `options`, each equally likely; none when there are no options. */
  def choose[A](options: Seq[A]): Option[(A, Dice)] =
    options match
      case first +: rest => Some(chooseAmong(first, rest*))
      case _             => None
