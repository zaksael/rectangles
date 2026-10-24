package dev.zaksael.rectangles.domain

enum CellKind:
  case Prize, Pitfall, Steal

/** `opponentSign` is 0 unless capturing also changes the other player's score. */
final case class CellEffect(capturerSign: Int, opponentSign: Int, points: Int)

/** `pairId` is numbered per cell, prize then pitfall then steal, as in Python; nothing reads it. */
final case class SpecialCell(kind: CellKind, location: Cell, pairId: Int)
