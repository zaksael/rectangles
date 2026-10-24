package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState

class RerollSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(size: Int, reroll: Boolean = true): GameState =
    GameState.initial(Rules(boardSize = size, reroll = reroll))

  private def one(state: GameState) = state.players(PlayerId.One)

  "a game with rerolls off" should "never allow one" in {
    val (rolled, _) = Turns.rollDice(game(19, reroll = false), ScriptedDice.of(4, 6)).value
    Rerolls.canReroll(rolled) shouldBe false
  }

  "a reroll from a placement choice" should "spend a charge and roll again" in {
    val (rolled, dice) = Turns.rollDice(game(6), ScriptedDice.of(2, 3, 4, 5)).value
    rolled.lastRoll shouldBe Some(Roll(2, 3))
    Rerolls.canReroll(rolled) shouldBe true
    val (again, _) = Turns.reroll(rolled, dice).value
    one(again).rerollsUsed shouldBe 1
    again.lastRoll shouldBe Some(Roll(4, 5))
    again.turn shouldBe TurnState.ChoosingPlacement
  }

  "reroll charges" should "run out after the limit, and a reroll with none left is refused" in {
    val start = Turns.rollDice(
      game(6),
      ScriptedDice(List.fill(Constants.REROLL_LIMIT + 1)(List(2, 3)).flatten),
    ).value
    val (last, dice) = (0 until Constants.REROLL_LIMIT).foldLeft(start) {
      case ((state, current), _) =>
        Turns.reroll(state, current).value
    }
    one(last).rerollsUsed shouldBe Constants.REROLL_LIMIT
    Rerolls.canReroll(last) shouldBe false
    Turns.reroll(last, dice) shouldBe Left(RuleError.WrongState)
  }

  "a reroll with no roll to discard" should "be refused" in {
    Turns.reroll(game(6), ScriptedDice.of(2, 3)) shouldBe Left(RuleError.WrongState)
  }

  private val deadRoll = ScriptedDice.of(6, 6)

  "a skip" should "wait to be recorded while a reroll charge is left" in {
    val (rolled, _) = Turns.rollDice(game(2), deadRoll).value
    rolled.turn shouldBe TurnState.Skipped
    one(rolled).consecutiveSkips shouldBe 0
    rolled.history shouldBe empty
  }

  it should "be recorded when the player confirms it" in {
    val (rolled, _) = Turns.rollDice(game(2), deadRoll).value
    val confirmed   = Turns.confirmSkip(rolled).value
    one(confirmed).consecutiveSkips shouldBe 1
    confirmed.history.map(_.placed) shouldBe Vector(None)
  }

  it should "be recorded once, at the roll, when no reroll can be spent" in {
    val (rolled, _) = Turns.rollDice(game(2, reroll = false), deadRoll).value
    one(rolled).consecutiveSkips shouldBe 1
    val confirmed = Turns.confirmSkip(rolled).value
    one(confirmed).consecutiveSkips shouldBe 1
    confirmed.history should have size 1
  }

  it should "never be recorded when it is rerolled away" in {
    val (rolled, dice) = Turns.rollDice(game(2), ScriptedDice.of(6, 6, 1, 1)).value
    val (again, _)     = Turns.reroll(rolled, dice).value
    one(again).rerollsUsed shouldBe 1
    one(again).consecutiveSkips shouldBe 0
    again.history shouldBe empty
    again.lastRoll shouldBe Some(Roll(1, 1))
  }
