package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

object Setup:
  /**
   * A new game for `rules`, its walls drawn first; with no pinned `starter`, a coin flip from
   * `dice` says who moves first.
   */
  def newGame(rules: Rules, starter: Option[PlayerId], dice: Dice): (GameState, Dice) =
    val (walls, afterWalls) =
      if rules.walls then Generation.wallEdges(rules, Set.empty, dice) else (Set.empty[Edge], dice)
    val (first, next) =
      starter.map((_, afterWalls)).getOrElse(afterWalls.choose(PlayerId.values.toSeq))
    val game = GameState.initial(rules, first)
    (game.copy(board = game.board.copy(wallEdges = walls)), next)
