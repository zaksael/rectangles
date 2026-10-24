package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.SpecialCell

object Setup:
  /**
   * A new game for `rules`, its prize cells, walls and obstacles drawn in that order, each avoiding
   * the ones before; with no pinned `starter`, a coin flip from `dice` says who moves first.
   */
  def newGame(rules: Rules, starter: Option[PlayerId], dice: Dice): (GameState, Dice) =
    val (prize, afterPrize) =
      if rules.prize then
        Generation.mirroredCellPairs(
          rules.boardSize,
          Constants.PRIZE_CELL_PAIRS,
          Set.empty,
          dice,
        )
      else (Set.empty[Cell], dice)
    val (walls, afterWalls) =
      if rules.walls then Generation.wallEdges(rules, prize, afterPrize)
      else (Set.empty[Edge], afterPrize)
    val (obstacles, afterObstacles) =
      if rules.obstacles then
        Generation.mirroredCellPairs(
          rules.boardSize,
          Constants.OBSTACLE_CELL_PAIRS,
          prize ++ Generation.wallCells(walls),
          afterWalls,
        )
      else (Set.empty[Cell], afterWalls)
    val (first, next) =
      starter.map((_, afterObstacles)).getOrElse(afterObstacles.choose(PlayerId.values.toSeq))
    val game = GameState.initial(rules, first)
    val specialCells = prize.toSeq.sortBy(c => (c.row, c.col)).zipWithIndex.map { (cell, index) =>
      SpecialCell(CellKind.Prize, cell, index)
    }
    (
      game.copy(board =
        game.board.copy(
          specialCells = specialCells.toSet,
          wallEdges = walls,
          obstacleCells = obstacles,
        )
      ),
      next,
    )
