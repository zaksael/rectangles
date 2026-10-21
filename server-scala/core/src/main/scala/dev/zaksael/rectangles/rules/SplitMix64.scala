package dev.zaksael.rectangles.rules

final case class SplitMix64(state: Long) extends Dice:
  def nextLong: (Long, SplitMix64) =
    val next   = state + 0x9e3779b97f4a7c15L
    val mixed1 = (next ^ (next >>> 30)) * 0xbf58476d1ce4e5b9L
    val mixed2 = (mixed1 ^ (mixed1 >>> 27)) * 0x94d049bb133111ebL
    (mixed2 ^ (mixed2 >>> 31), SplitMix64(next))

  // shortcut: plain modulo, a bias of about 2^-60 for a die, upgrade if a range ever nears 2^32.
  def between(lo: Int, hi: Int): (Int, Dice) =
    val (bits, rest) = nextLong
    (lo + Math.floorMod(bits, (hi - lo + 1).toLong).toInt, rest)
