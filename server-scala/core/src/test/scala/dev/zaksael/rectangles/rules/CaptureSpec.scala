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
import dev.zaksael.rectangles.withSpecialCells

class CaptureSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def captures(state: GameState, who: PlayerId, kind: CellKind): Int =
    state.players(who).specialCaptures.getOrElse(kind, 0)

  "a placement over a prize cell" should "capture it for the placer only" in {
    val start =
      withSpecialCells(Rules(boardSize = 11), CellKind.Prize, Cell(0, 10), Cell(10, 0), Cell(5, 5))
    val (rolled, _) = Turns.rollDice(start, ScriptedDice.of(6, 6)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 6, 6).value
    captures(state, PlayerId.One, CellKind.Prize) shouldBe 1
    captures(state, PlayerId.Two, CellKind.Prize) shouldBe 0
  }

  it should "capture every prize cell it covers, however many" in {
    val start =
      withSpecialCells(Rules(boardSize = 11), CellKind.Prize, Cell(0, 10), Cell(10, 0), Cell(5, 5))
    // P1 takes rows 0-5 x cols 0-4, P2 a corner cell, then P1 spans cols 5-10 over two prizes.
    val moves = List((Cell(0, 0), 5, 6), (Cell(10, 10), 1, 1), (Cell(0, 5), 6, 6))
    val (state, _) = moves.foldLeft((start, ScriptedDice.of(5, 6, 1, 1, 6, 6): Dice)) {
      case ((current, dice), (topLeft, width, height)) =>
        val (rolled, next) = Turns.rollDice(current, dice).value
        (Turns.endTurn(Turns.attemptPlace(rolled, topLeft, width, height).value), next)
    }
    captures(state, PlayerId.One, CellKind.Prize) shouldBe 2
    captures(state, PlayerId.Two, CellKind.Prize) shouldBe 0
  }

  "a placement over a pitfall cell" should "capture it and cost the placer its penalty even with the rule off" in {
    val (rolled, _) =
      Turns.rollDice(
        withSpecialCells(Rules(boardSize = 11), CellKind.Pitfall, Cell(5, 5)),
        ScriptedDice.of(6, 6),
      ).value
    val state = Turns.attemptPlace(rolled, Cell(0, 0), 6, 6).value
    captures(state, PlayerId.One, CellKind.Pitfall) shouldBe 1
    Scoring.total(state, PlayerId.One) shouldBe 36 - Constants.PITFALL_PENALTY_POINTS
  }
