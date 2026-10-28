package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.ScoreBreakdown
import dev.zaksael.rectangles.generated
import dev.zaksael.rectangles.withSpecialCells

class StealSpec extends AnyFlatSpec with Matchers with EitherValues:
  "stolen points" should "move from the opponent to the capturer, and scores have no floor" in {
    val (rolled, _) = Turns.rollDice(
      withSpecialCells(Rules(boardSize = 11, steal = true), CellKind.Steal, Cell(5, 5)),
      ScriptedDice.of(6, 6),
    ).value
    val state = Turns.attemptPlace(rolled, Cell(0, 0), 6, 6).value
    val one   = state.players(PlayerId.One)
    val two   = state.players(PlayerId.Two)
    one.specialCaptures.getOrElse(CellKind.Steal, 0) shouldBe 1
    two.specialCaptures.getOrElse(CellKind.Steal, 0) shouldBe 0
    Scoring.total(state, PlayerId.One) shouldBe one.totalArea + Constants.STEAL_POINTS
    Scoring.total(state, PlayerId.Two) shouldBe two.totalArea - Constants.STEAL_POINTS
    Scoring.total(state, PlayerId.Two) should be < 0
  }

  "steal cells" should "never overlap prize, wall, obstacle or pitfall cells" in {
    val found =
      for seed <- 0 until 30
      yield
        val board = generated(
          Rules(prize = true, walls = true, obstacles = true, pitfall = true, steal = true),
          seed.toLong,
        ).board
        val steals = board.cellsOfKind(CellKind.Steal)
        steals.intersect(board.cellsOfKind(CellKind.Prize)) shouldBe empty
        steals.intersect(board.cellsOfKind(CellKind.Pitfall)) shouldBe empty
        steals.intersect(Generation.wallCells(board.wallEdges)) shouldBe empty
        steals.intersect(board.obstacleCells) shouldBe empty
        steals
    found.exists(_.nonEmpty) shouldBe true
  }

  it should "be one mirrored pair clear of the start corners" in {
    val found =
      for
        size <- List(11, 19)
        seed <- 0 until 30
      yield
        val cells = generated(Rules(boardSize = size, steal = true), seed.toLong).board
          .cellsOfKind(CellKind.Steal)
        cells.size should be <= 2 * Constants.STEAL_CELL_PAIRS
        cells.map(Generation.mirrorCell(_, size)) shouldBe cells
        cells.foreach(Generation.nearStartCorner(_, size) shouldBe false)
        cells
    found.exists(_.nonEmpty) shouldBe true
  }

  it should "be empty on a board too small for any candidate" in {
    val board = generated(Rules(boardSize = 6, steal = true)).board
    board.cellsOfKind(CellKind.Steal) shouldBe empty
  }

  "the score history" should "carry a steal at each step and end at the live totals" in {
    val moves = List((Cell(0, 0), 6, 6), (Cell(9, 9), 2, 2))
    val (state, _) = moves.foldLeft((
      withSpecialCells(Rules(boardSize = 11, steal = true), CellKind.Steal, Cell(5, 5)),
      ScriptedDice.of(6, 6, 2, 2): Dice,
    )) {
      case ((current, dice), (topLeft, width, height)) =>
        val (rolled, next) = Turns.rollDice(current, dice).value
        (Turns.endTurn(Turns.attemptPlace(rolled, topLeft, width, height).value), next)
    }
    val totals = Scoring.breakdownHistory(state).map(_.view.mapValues(_.total).toMap)
    val ten    = Constants.STEAL_POINTS
    totals shouldBe Vector(
      Map(PlayerId.One -> (36 + ten), PlayerId.Two -> -ten),
      Map(PlayerId.One -> (36 + ten), PlayerId.Two -> (4 - ten)),
    )
    totals.last shouldBe Map(
      PlayerId.One -> Scoring.total(state, PlayerId.One),
      PlayerId.Two -> Scoring.total(state, PlayerId.Two),
    )
  }

  "the breakdown history" should "move a steal from the opponent to the capturer" in {
    val (rolled, _) = Turns.rollDice(
      withSpecialCells(Rules(boardSize = 11, steal = true), CellKind.Steal, Cell(0, 0)),
      ScriptedDice.of(2, 2),
    ).value
    val state = Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value
    Scoring.breakdownHistory(state) shouldBe Vector(
      Map(
        PlayerId.One -> ScoreBreakdown(area = 4, steal = Constants.STEAL_POINTS),
        PlayerId.Two -> ScoreBreakdown(steal = -Constants.STEAL_POINTS),
      )
    )
  }
