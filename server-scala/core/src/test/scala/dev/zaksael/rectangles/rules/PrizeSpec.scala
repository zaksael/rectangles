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
import dev.zaksael.rectangles.generated

class PrizeSpec extends AnyFlatSpec with Matchers:
  private def prizes(rules: Rules, dice: Dice): Set[Cell] =
    Setup.newGame(rules, Some(PlayerId.One), dice)._1.board.cellsOfKind(CellKind.Prize)

  "prize cells" should "be symmetric and clear of the start corners on odd boards" in {
    val found =
      for
        size <- List(11, 19)
        seed <- 0 until 30
      yield
        val cells = prizes(Rules(boardSize = size, prize = true), SplitMix64(seed.toLong))
        cells.size should be <= 2 * Constants.PRIZE_CELL_PAIRS
        cells.map(Generation.mirrorCell(_, size)) shouldBe cells
        cells.foreach(Generation.nearStartCorner(_, size) shouldBe false)
        cells
    found.exists(_.nonEmpty) shouldBe true
  }

  it should "be empty on a board too small for any candidate" in {
    prizes(Rules(boardSize = 6, prize = true), SplitMix64(0L)) shouldBe empty
  }

  it should "never include the self-mirroring centre cell" in {
    for size <- List(11, 19) do
      val cells = prizes(Rules(boardSize = size, prize = true), ScriptedDice(List.fill(20)(0)))
      cells should not be empty
      cells should not contain Cell(size / 2, size / 2)
      cells.size % 2 shouldBe 0
  }

  it should "stay the minimum special cell distance apart, like obstacle cells" in {
    for seed <- 0 until 30 do
      val board = generated(Rules(prize = true, obstacles = true), seed.toLong).board
      for
        cells <- List(board.cellsOfKind(CellKind.Prize), board.obstacleCells)
        a     <- cells
        b     <- cells if a != b
      do chebyshev(a, b) should be >= Constants.MIN_SPECIAL_CELL_DISTANCE
  }
