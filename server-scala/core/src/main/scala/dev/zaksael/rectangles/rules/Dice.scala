package dev.zaksael.rectangles.rules

/** A source of dice: every draw returns the value and the dice to draw the next one from. */
trait Dice:
  /** A value in `lo` to `hi`, both included. */
  def between(lo: Int, hi: Int): (Int, Dice)
