package dev.zaksael.rectangles.domain

final case class Roll(first: Int, second: Int)

/**
 * `placed` is None for a skip; `wildcardOriginalRoll` is set on every turn whose roll opened the
 * wildcard picker, whether the number was edited or kept.
 */
final case class TurnRecord(
    playerId: PlayerId,
    roll: Roll,
    placed: Option[Rectangle],
    wildcardOriginalRoll: Option[Roll] = None,
)
