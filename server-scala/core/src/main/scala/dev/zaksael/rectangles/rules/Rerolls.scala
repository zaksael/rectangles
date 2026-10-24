package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Rules

object Rerolls:
  /** How many rerolls a player may spend in the whole game. */
  def limit(rules: Rules): Int = if rules.reroll then Constants.REROLL_LIMIT else 0

  def canReroll(state: GameState): Boolean =
    state.players(state.current).rerollsUsed < limit(state.rules)
