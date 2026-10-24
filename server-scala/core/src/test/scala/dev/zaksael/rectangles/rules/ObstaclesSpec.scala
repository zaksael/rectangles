package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.chebyshev
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

class ObstaclesSpec extends AnyFlatSpec with Matchers:
  private def newGame(rules: Rules, seed: Long) =
    Setup.newGame(rules, Some(PlayerId.One), SplitMix64(seed))._1

  "a game with obstacles off" should "have no obstacle cells" in {
    newGame(Rules(boardSize = 11), 0L).board.obstacleCells shouldBe empty
  }

  "obstacle cells" should "be symmetric, clear of the start corners and spread apart" in {
    val rules = Rules(obstacles = true)
    for seed <- 0 until 30 do
      val cells = newGame(rules, seed.toLong).board.obstacleCells
      cells should not be empty
      cells.foreach { cell =>
        cells should contain(Generation.mirrorCell(cell, rules.boardSize))
        Generation.nearStartCorner(cell, rules.boardSize) shouldBe false
      }
      for
        a <- cells
        b <- cells if a != b
      do chebyshev(a, b) should be >= Constants.MIN_SPECIAL_CELL_DISTANCE
  }

  it should "stay off the wall cells when walls are on" in {
    for seed <- 0 until 30 do
      val board = newGame(Rules(obstacles = true, walls = true), seed.toLong).board
      board.obstacleCells should not be empty
      board.obstacleCells.intersect(board.wallEdges.flatMap(edge => Set(edge.a, edge.b))) shouldBe
        empty
  }

  it should "be symmetric, bounded and clear of the corners, prizes and walls on odd boards" in {
    for
      size  <- List(11, 19)
      extra <- List(Rules(), Rules(prize = true), Rules(walls = true))
    do
      val board = Setup
        .newGame(
          extra.copy(boardSize = size, obstacles = true),
          Some(PlayerId.One),
          ScriptedDice(List.fill(20)(0)),
        )
        ._1
        .board
      val cells = board.obstacleCells
      cells should not be empty
      cells.size should be <= 2 * Constants.OBSTACLE_CELL_PAIRS
      cells.map(Generation.mirrorCell(_, size)) shouldBe cells
      cells.foreach(Generation.nearStartCorner(_, size) shouldBe false)
      cells.intersect(board.cellsOfKind(CellKind.Prize)) shouldBe empty
      cells.intersect(Generation.wallCells(board.wallEdges)) shouldBe empty
  }
