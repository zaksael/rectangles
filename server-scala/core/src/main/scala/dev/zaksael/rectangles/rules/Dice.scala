package dev.zaksael.rectangles.rules

/** A source of dice: every draw returns the value and the dice to draw the next one from. */
trait Dice:
  /** A value in `lo` to `hi`, both included. */
  def between(lo: Int, hi: Int): (Int, Dice)

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
