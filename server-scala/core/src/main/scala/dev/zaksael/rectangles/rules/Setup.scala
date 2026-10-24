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
   * A new game for `rules`, its prize cells, walls, obstacles, pitfalls and steal cells drawn in
   * that order, each avoiding the ones before; with no pinned `starter`, a coin flip from `dice`
   * says who moves first.
   */
  def newGame(rules: Rules, starter: Option[PlayerId], dice: Dice): (GameState, Dice) =
    def cells(on: Boolean, count: Int, occupied: Set[Cell], from: Dice): (Set[Cell], Dice) =
      if on then Generation.mirroredCellPairs(rules.boardSize, count, occupied, from)
      else (Set.empty, from)
    val (prize, afterPrize) = cells(rules.prize, Constants.PRIZE_CELL_PAIRS, Set.empty, dice)
    val (walls, afterWalls) =
      if rules.walls then Generation.wallEdges(rules, prize, afterPrize)
      else (Set.empty[Edge], afterPrize)
    val wallCells = Generation.wallCells(walls)
    val (obstacles, afterObstacles) =
      cells(rules.obstacles, Constants.OBSTACLE_CELL_PAIRS, prize ++ wallCells, afterWalls)
    val (pitfall, afterPitfall) = cells(
      rules.pitfall,
      Constants.PITFALL_CELL_PAIRS,
      prize ++ wallCells ++ obstacles,
      afterObstacles,
    )
    val (steal, afterSteal) = cells(
      rules.steal,
      Constants.STEAL_CELL_PAIRS,
      prize ++ wallCells ++ obstacles ++ pitfall,
      afterPitfall,
    )
    val (first, next) =
      starter.map((_, afterSteal)).getOrElse(afterSteal.choose(PlayerId.values.toSeq))
    val game = GameState.initial(rules, first)
    val specialCells =
      List(CellKind.Prize -> prize, CellKind.Pitfall -> pitfall, CellKind.Steal -> steal)
        .flatMap((kind, cells) => cells.toSeq.sortBy(c => (c.row, c.col)).map(kind -> _))
        .zipWithIndex
        .map { case ((kind, cell), index) => SpecialCell(kind, cell, index) }
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
