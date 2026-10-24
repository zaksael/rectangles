package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

class ObstaclesSpec extends AnyFlatSpec with Matchers:
  private def chebyshev(a: Cell, b: Cell): Int =
    math.max(math.abs(a.row - b.row), math.abs(a.col - b.col))

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
