package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState

class WildcardSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(size: Int, wildcard: Boolean = true, reroll: Boolean = false): GameState =
    GameState.initial(Rules(boardSize = size, wildcard = wildcard, reroll = reroll))

  private def rolled(state: GameState, values: Int*): (GameState, Dice) =
    Turns.rollDice(state, ScriptedDice.of(values*)).value

  "a game with the wildcard off" should "never offer the picker" in {
    val (state, _) = rolled(game(19, wildcard = false), 4, 6)
    state.lastRoll shouldBe Some(Roll(4, 6))
    state.wildcard shouldBe None
    state.turn shouldBe TurnState.ChoosingPlacement
  }

  "a roll that is not a double" should "not offer the picker" in {
    val (state, _) = rolled(game(6), 3, 5)
    state.lastRoll shouldBe Some(Roll(3, 5))
    state.turn shouldBe TurnState.ChoosingPlacement
    state.wildcard shouldBe None
  }

  "a double" should "let the player change one die" in {
    val (state, _) = rolled(game(6), 5, 5, 0)
    state.lastRoll shouldBe Some(Roll(5, 5))
    state.turn shouldBe TurnState.ChoosingWildcard
    state.wildcard.map(_.editableIndex) shouldBe Some(Some(0))
    state.wildcard.map(_.originalRoll) shouldBe Some(Roll(5, 5))
    val chosen = Turns.chooseWildcard(state, 6).value
    chosen.lastRoll shouldBe Some(Roll(6, 5))
    chosen.wildcard.flatMap(_.editableIndex) shouldBe None
    chosen.turn shouldBe TurnState.ChoosingPlacement
  }

  it should "skip when the changed die leaves no placement" in {
    val (state, _) = rolled(game(4), 3, 3, 1)
    state.turn shouldBe TurnState.ChoosingWildcard
    val chosen = Turns.chooseWildcard(state, 6).value
    chosen.lastRoll shouldBe Some(Roll(3, 6))
    chosen.turn shouldBe TurnState.Skipped
  }

  it should "skip the picker when no value could be placed" in {
    val (state, _) = rolled(game(4), 6, 6, 1)
    state.turn shouldBe TurnState.Skipped
    state.wildcard.flatMap(_.editableIndex) shouldBe None
    state.history.lastOption.flatMap(_.wildcardOriginalRoll) shouldBe Some(Roll(6, 6))
  }

  "the placements for a wildcard value" should "use the value in place of the editable die" in {
    val (state, _) = rolled(game(6), 5, 5, 0)
    val spots      = Turns.legalPlacementsForValue(state, 3)
    spots.keySet shouldBe Set(Roll(3, 5), Roll(5, 3))
    val player = state.players(PlayerId.One)
    spots(Roll(3, 5)) shouldBe Placement.legalTopLefts(state.board, player, 3, 5)
    spots(Roll(5, 3)) shouldBe Placement.legalTopLefts(state.board, player, 5, 3)
  }

  "a resolved wildcard" should "give no bonus turn and leave no wildcard behind" in {
    val (state, _) = rolled(game(6), 3, 3, 1)
    val chosen     = Turns.chooseWildcard(state, 5).value
    chosen.lastRoll shouldBe Some(Roll(3, 5))
    val placed = Turns.attemptPlace(chosen, Cell(0, 0), 3, 5).value
    Turns.checkGameOver(placed).turn should not be TurnState.GameOver
    val next = Turns.endTurn(placed)
    next.current shouldBe PlayerId.Two
    next.wildcard shouldBe None
  }

  "a reroll from the picker" should "discard the pending wildcard" in {
    val (state, dice) =
      Turns.rollDice(game(6, reroll = true), ScriptedDice.of(3, 3, 0, 4, 5)).value
    state.turn shouldBe TurnState.ChoosingWildcard
    val (again, _) = Turns.reroll(state, dice).value
    again.lastRoll shouldBe Some(Roll(4, 5))
    again.wildcard shouldBe None
    again.turn shouldBe TurnState.ChoosingPlacement
  }

  "choosing a wildcard value" should "be refused outside the picker" in {
    val (state, _) = rolled(game(19, wildcard = false), 4, 6)
    Turns.chooseWildcard(state, 3) shouldBe Left(RuleError.WrongState)
  }

  it should "be refused for a value outside 1 to 6" in {
    val (state, _) = rolled(game(6), 3, 3, 0)
    Turns.chooseWildcard(state, 0) shouldBe Left(RuleError.IllegalWildcardValue)
    Turns.chooseWildcard(state, 7) shouldBe Left(RuleError.IllegalWildcardValue)
  }
