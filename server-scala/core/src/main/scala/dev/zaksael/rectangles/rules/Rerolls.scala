package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Player
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

object Rerolls:
  /**
   * How many rerolls `player` may spend in the whole game, the comeback nudge's charge included.
   */
  def limit(rules: Rules, player: Player): Int =
    (if rules.reroll then Constants.REROLL_LIMIT else 0) +
      (if rules.comebackNudge && player.comebackNudgeGranted then
         Constants.COMEBACK_NUDGE_EXTRA_REROLLS
       else 0)

  def canReroll(state: GameState): Boolean =
    val player = state.players(state.current)
    player.rerollsUsed < limit(state.rules, player)

  /** The score gap, in whole cells rounded up, that earns the trailing player the nudge. */
  def comebackThreshold(boardSize: Int): Int =
    math.ceil(boardSize * boardSize * Constants.COMEBACK_NUDGE_THRESHOLD_FRACTION).toInt

  /** Permanently grants the trailing player the nudge once the score gap reaches the threshold. */
  def maybeGrantNudge(state: GameState): GameState =
    if !state.rules.comebackNudge then state
    else
      val trailing =
        if Scoring.total(state, PlayerId.One) < Scoring.total(state, PlayerId.Two) then PlayerId.One
        else PlayerId.Two
      val gap = Scoring.total(state, trailing.other) - Scoring.total(state, trailing)
      if gap >= comebackThreshold(state.rules.boardSize) then
        state.copy(players =
          state.players.updated(trailing, state.players(trailing).copy(comebackNudgeGranted = true))
        )
      else state
