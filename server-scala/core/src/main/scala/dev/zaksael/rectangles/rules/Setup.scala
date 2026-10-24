package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

object Setup:
  /**
   * A new game for `rules`; with no pinned `starter`, a coin flip from `dice` says who moves first.
   */
  def newGame(rules: Rules, starter: Option[PlayerId], dice: Dice): (GameState, Dice) =
    val (first, next) = starter.map((_, dice)).getOrElse(dice.choose(PlayerId.values.toSeq))
    (GameState.initial(rules, first), next)
