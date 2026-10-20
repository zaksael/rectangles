package dev.zaksael.rectangles.domain

/** `value` is the number the wire uses. */
enum PlayerId(val value: Int):
  case One extends PlayerId(1)
  case Two extends PlayerId(2)

  def other: PlayerId = this match
    case One => Two
    case Two => One

final case class Player(
    id: PlayerId,
    name: String,
    startCorner: Cell,
    pieces: Vector[Rectangle] = Vector.empty,
    consecutiveSkips: Int = 0,
    specialCaptures: Map[CellKind, Int] = Map.empty,
    rerollsUsed: Int = 0,
    comebackNudgeGranted: Boolean = false,
):
  def totalArea: Int = pieces.map(_.area).sum

  def hasMoved: Boolean = pieces.nonEmpty

final case class ScoreBreakdown(
    area: Int = 0,
    prize: Int = 0,
    pitfall: Int = 0,
    steal: Int = 0,
    enclosure: Int = 0,
):
  def total: Int = area + prize + pitfall + steal + enclosure
