package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.domain.TurnState

class TurnFlowSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(boardSize: Int = 6): GameState = GameState.initial(Rules(boardSize = boardSize))

  /** Player One owns a 3x4 block and a 1x3 column on a 4x4 board: only (3, 3) is left. */
  private def stuckGame(): GameState =
    val start  = game(4)
    val first  = Placement.place(start.board, start.players(PlayerId.One), Cell(0, 0), 3, 4)
    val second = Placement.place(first.board, first.player, Cell(0, 3), 1, 3)
    start.copy(board = second.board, players = start.players.updated(PlayerId.One, second.player))

  "rolling the dice" should "take the roll from the dice" in {
    val (state, _) = Turns.rollDice(game(), ScriptedDice.of(4, 6)).value
    state.lastRoll shouldBe Some(Roll(4, 6))
  }

  "a placement" should "pass the turn to the other player" in {
    val (rolled, _) = Turns.rollDice(game(), ScriptedDice.of(2, 3)).value
    rolled.turn shouldBe TurnState.ChoosingPlacement
    val next = Turns.endTurn(Turns.attemptPlace(rolled, Cell(0, 0), 2, 3).value)
    next.current shouldBe PlayerId.Two
    next.turn shouldBe TurnState.AwaitingRoll
  }

  "a roll with no legal placement" should "skip the turn" in {
    val (state, _) = Turns.rollDice(stuckGame(), ScriptedDice.of(6, 6)).value
    state.turn shouldBe TurnState.Skipped
    state.lastRoll shouldBe Some(Roll(6, 6))
  }

  "a double without the wildcard rule" should "pass the turn like any other roll" in {
    val (rolled, _) = Turns.rollDice(game(), ScriptedDice.of(2, 2)).value
    rolled.turn shouldBe TurnState.ChoosingPlacement
    val next = Turns.endTurn(Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value)
    next.current shouldBe PlayerId.Two
  }

  "placing at an illegal top-left" should "be rejected and leave the turn as it was" in {
    val (rolled, _) = Turns.rollDice(game(), ScriptedDice.of(2, 2)).value
    Turns.attemptPlace(rolled, Cell(3, 3), 2, 2) shouldBe Left(RuleError.IllegalPlacement)
    rolled.turn shouldBe TurnState.ChoosingPlacement
    rolled.history shouldBe empty
  }

  "placing before a roll" should "be rejected" in {
    Turns.attemptPlace(game(), Cell(0, 0), 1, 1) shouldBe Left(RuleError.IllegalPlacement)
  }

  "rolling twice in one turn" should "be rejected" in {
    val (rolled, dice) = Turns.rollDice(game(), ScriptedDice.of(2, 2, 3, 3)).value
    Turns.rollDice(rolled, dice).map(_._1) shouldBe Left(RuleError.WrongState)
  }

  "ending the turn after the game is over" should "change nothing" in {
    val over = game(4).copy(turn = TurnState.GameOver)
    Turns.endTurn(over) shouldBe over
  }

  "a placement" should "append a history record" in {
    val (rolled, _) = Turns.rollDice(game(), ScriptedDice.of(2, 2)).value
    val placed      = Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value
    placed.history shouldBe Vector(
      TurnRecord(PlayerId.One, Roll(2, 2), Some(Rectangle(Cell(0, 0), 2, 2, PlayerId.One)))
    )
  }

  it should "record the roll as rolled when the piece is placed turned" in {
    val (rolled, _) = Turns.rollDice(game(), ScriptedDice.of(2, 3)).value
    val placed      = Turns.attemptPlace(rolled, Cell(0, 0), 3, 2).value
    placed.history.map(_.roll) shouldBe Vector(Roll(2, 3))
  }

  "a skip" should "append a history record without a piece" in {
    val (state, _) = Turns.rollDice(stuckGame(), ScriptedDice.of(6, 6)).value
    state.history shouldBe Vector(TurnRecord(PlayerId.One, Roll(6, 6), None))
  }

  it should "count toward the player's skip streak, and only theirs" in {
    val (state, _) = Turns.rollDice(stuckGame(), ScriptedDice.of(6, 6)).value
    state.players(PlayerId.One).consecutiveSkips shouldBe 1
    state.players(PlayerId.Two).consecutiveSkips shouldBe 0
  }

  "a new game" should "start with an empty history, a roll to make and the starter on turn" in {
    val state = GameState.initial(Rules(boardSize = 6), PlayerId.Two)
    state.history shouldBe empty
    state.turn shouldBe TurnState.AwaitingRoll
    state.current shouldBe PlayerId.Two
  }
