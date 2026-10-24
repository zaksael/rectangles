package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.placed

class SelfEnclosedSpec extends AnyFlatSpec with Matchers:
  private val penalty = Constants.SELF_ENCLOSED_PENALTY_PER_CELL
  private val ring    = List(Cell(1, 2), Cell(3, 2), Cell(2, 1), Cell(2, 3))

  private def game(on: Boolean): GameState =
    GameState.initial(Rules(boardSize = 6, selfEnclosedPenalty = on))

  private def ringed(on: Boolean): GameState =
    placed(
      ring.foldLeft(game(on))((state, cell) => placed(state, PlayerId.One, cell, 1, 1)),
      PlayerId.Two,
      Cell(5, 5),
      1,
      1,
    )

  "a game with the penalty off" should "score the plain area" in {
    val state = placed(game(false), PlayerId.One, Cell(0, 0), 2, 2)
    Scoring.total(state, PlayerId.One) shouldBe 4
    Scoring.total(ringed(false), PlayerId.One) shouldBe 4
  }

  "a hole only its owner encloses" should "cost that player a penalty per cell and nobody else" in {
    val state = ringed(true)
    state.players(PlayerId.One).totalArea shouldBe 4
    Scoring.total(state, PlayerId.One) shouldBe 4 - penalty
    Scoring.total(state, PlayerId.Two) shouldBe state.players(PlayerId.Two).totalArea
  }

  it should "stop costing once it is filled" in {
    val filled = placed(ringed(true), PlayerId.One, Cell(2, 2), 1, 1)
    Scoring.total(filled, PlayerId.One) shouldBe filled.players(PlayerId.One).totalArea
  }

  private def record(who: PlayerId, cell: Cell): TurnRecord =
    TurnRecord(who, Roll(1, 1), Some(Rectangle(cell, 1, 1, who)))

  "the score history" should "apply the penalty at the step the hole closes and repeat it on a skip" in {
    val state = game(true).copy(history =
      Vector(
        record(PlayerId.One, Cell(1, 2)),
        record(PlayerId.Two, Cell(5, 5)),
        record(PlayerId.One, Cell(3, 2)),
        TurnRecord(PlayerId.Two, Roll(1, 1), None),
        record(PlayerId.One, Cell(2, 1)),
        record(PlayerId.One, Cell(2, 3)),
      )
    )
    val totals = Scoring.breakdownHistory(state).map(_.view.mapValues(_.total).toMap)
    totals.map(_(PlayerId.One)) shouldBe Vector(1, 1, 2, 2, 3, 4 - penalty)
    totals.map(_(PlayerId.Two)) shouldBe Vector(0, 1, 1, 1, 1, 1)
  }

  "the breakdown history" should "show the enclosure term from the step it appears" in {
    val state = game(true).copy(history = ring.map(record(PlayerId.One, _)).toVector)
    val steps = Scoring.breakdownHistory(state).map(_(PlayerId.One))
    steps.map(_.enclosure) shouldBe Vector(0, 0, 0, -penalty)
    steps.map(_.area) shouldBe Vector(1, 2, 3, 4)
  }
