package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.ScoreBreakdown
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.placed

class PitfallSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def pitfallGame(cells: Cell*): GameState =
    val state = GameState.initial(Rules(boardSize = 11, pitfall = true))
    state.copy(board =
      state.board.copy(specialCells =
        cells.zipWithIndex.map((cell, index) => SpecialCell(CellKind.Pitfall, cell, index)).toSet
      )
    )

  "a game with pitfalls off" should "have no pitfall cells and no penalty" in {
    val state = GameState.initial(Rules(boardSize = 8))
    state.board.cellsOfKind(CellKind.Pitfall) shouldBe empty
    val moved = placed(state, PlayerId.One, Cell(0, 0), 2, 2)
    moved.players(PlayerId.One).specialCaptures.getOrElse(CellKind.Pitfall, 0) shouldBe 0
    Scoring.total(moved, PlayerId.One) shouldBe 4
  }

  "pitfall cells" should "never overlap prize, wall or obstacle cells" in {
    val found =
      for seed <- 0 until 30
      yield
        val board = Setup
          .newGame(
            Rules(prize = true, walls = true, obstacles = true, pitfall = true),
            Some(PlayerId.One),
            SplitMix64(seed.toLong),
          )
          ._1
          .board
        val pitfalls = board.cellsOfKind(CellKind.Pitfall)
        pitfalls.intersect(board.cellsOfKind(CellKind.Prize)) shouldBe empty
        pitfalls.intersect(Generation.wallCells(board.wallEdges)) shouldBe empty
        pitfalls.intersect(board.obstacleCells) shouldBe empty
        pitfalls
    found.exists(_.nonEmpty) shouldBe true
  }

  it should "be empty on a board too small for any candidate" in {
    val board = Setup
      .newGame(Rules(boardSize = 6, pitfall = true), Some(PlayerId.One), SplitMix64(0L))
      ._1
      .board
    board.cellsOfKind(CellKind.Pitfall) shouldBe empty
  }

  "a pitfall" should "cost the placer its penalty, and the score has no floor" in {
    val (rolled, _) = Turns.rollDice(pitfallGame(Cell(5, 5)), ScriptedDice.of(6, 6)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 6, 6).value
    val one         = state.players(PlayerId.One)
    one.specialCaptures.getOrElse(CellKind.Pitfall, 0) shouldBe 1
    state.players(PlayerId.Two).specialCaptures.getOrElse(CellKind.Pitfall, 0) shouldBe 0
    Scoring.total(state, PlayerId.One) shouldBe one.totalArea - Constants.PITFALL_PENALTY_POINTS
    val sunk = state.copy(players =
      state.players.updated(
        PlayerId.One,
        one.copy(specialCaptures = Map(CellKind.Pitfall -> 100)),
      )
    )
    Scoring.total(sunk, PlayerId.One) should be < 0
  }

  "the breakdown history" should "charge a pitfall to the capturer only" in {
    val (rolled, _) = Turns.rollDice(pitfallGame(Cell(0, 0)), ScriptedDice.of(2, 2)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value
    Scoring.breakdownHistory(state) shouldBe Vector(
      Map(
        PlayerId.One -> ScoreBreakdown(area = 4, pitfall = -Constants.PITFALL_PENALTY_POINTS),
        PlayerId.Two -> ScoreBreakdown(),
      )
    )
  }
