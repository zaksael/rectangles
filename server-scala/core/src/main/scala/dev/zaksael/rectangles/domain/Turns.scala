package dev.zaksael.rectangles.domain

final case class Roll(first: Int, second: Int)

/**
 * `placed` is None for a skip; `wildcardOriginalRoll` is set only when the wildcard number was
 * edited.
 */
final case class TurnRecord(
    playerId: PlayerId,
    roll: Roll,
    placed: Option[Rectangle],
    wildcardOriginalRoll: Option[Roll] = None,
)
