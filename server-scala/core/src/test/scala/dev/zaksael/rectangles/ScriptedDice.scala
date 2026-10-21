package dev.zaksael.rectangles

import dev.zaksael.rectangles.rules.Dice

/** Dice that return the given values in order, whatever range is asked for. */
final case class ScriptedDice(values: List[Int]) extends Dice:
  def between(lo: Int, hi: Int): (Int, Dice) =
    (values.headOption.getOrElse(lo), ScriptedDice(values.drop(1)))

object ScriptedDice:
  def of(values: Int*): ScriptedDice = ScriptedDice(values.toList)
