package dev.zaksael.rectangles.domain

enum CellKind:
  case Prize, Pitfall, Steal

/** `opponentSign` is 0 unless capturing also changes the other player's score. */
final case class CellEffect(capturerSign: Int, opponentSign: Int, points: Int)

/** `pairId` groups a mirrored pair and is unique across kinds on one board. */
final case class SpecialCell(kind: CellKind, location: Cell, pairId: Int)
