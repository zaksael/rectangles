package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

/** One player's finished round: their area, special cells captured, and total score. */
final case class PlayerRound(
    area: Int,
    prizeCaptured: Int,
    pitfallCaptured: Int,
    stealCaptured: Int,
    total: Int,
)

final case class RoundResult(players: Map[PlayerId, PlayerRound])

/**
 * A fixed number of rounds on the same rules, scored by the sum of every round's total. It always
 * plays out every round: there is no early clinch.
 */
final case class Series(length: Int, rules: Rules, rounds: Vector[RoundResult] = Vector.empty):
  def gamesPlayed: Int = rounds.size

  def scores: Map[PlayerId, Int] =
    PlayerId.values.map(who => who -> rounds.map(_.players(who).total).sum).toMap

  def isComplete: Boolean = gamesPlayed >= length

  /** None when the totals are equal. */
  def winner: Option[PlayerId] =
    val totals = scores
    if totals(PlayerId.One) > totals(PlayerId.Two) then Some(PlayerId.One)
    else if totals(PlayerId.Two) > totals(PlayerId.One) then Some(PlayerId.Two)
    else None

  /** The series after a finished game is added as its next round. */
  def record(state: GameState): Series =
    def round(who: PlayerId): PlayerRound =
      val player = state.players(who)
      PlayerRound(
        area = player.totalArea,
        prizeCaptured = player.specialCaptures.getOrElse(CellKind.Prize, 0),
        pitfallCaptured = player.specialCaptures.getOrElse(CellKind.Pitfall, 0),
        stealCaptured = player.specialCaptures.getOrElse(CellKind.Steal, 0),
        total = Scoring.total(state, who),
      )
    copy(rounds = rounds :+ RoundResult(PlayerId.values.map(who => who -> round(who)).toMap))

  /** The next round's game: the starter alternates, beginning with Player One. */
  def newGame(dice: Dice): (GameState, Dice) =
    val starter = if gamesPlayed % 2 == 0 then PlayerId.One else PlayerId.Two
    Setup.newGame(rules, Some(starter), dice)
