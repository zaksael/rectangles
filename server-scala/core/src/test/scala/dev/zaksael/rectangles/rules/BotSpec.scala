package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.placed
import dev.zaksael.rectangles.withSpecialCells

class BotSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def rolled(state: GameState, dice: Int*): GameState =
    Turns.rollDice(state, ScriptedDice(dice.toList)).value._1

  private def small: GameState = GameState.initial(Rules(boardSize = 6))

  private val six = Rules(boardSize = 6)

  private def greedy(state: GameState): Candidate =
    Bot.choosePlacement(state, BotDifficulty.Greedy, ScriptedDice.of())._1

  "a Greedy placement" should "capture a Prize" in {
    val state = rolled(
      placed(withSpecialCells(six, CellKind.Prize, Cell(3, 3)), PlayerId.One, Cell(2, 3), 1, 1),
      1,
      1,
    )
    greedy(state) shouldBe Candidate(Cell(3, 3), 1, 1)
  }

  it should "capture a Steal cell over a plain cell" in {
    val state = rolled(
      placed(withSpecialCells(six, CellKind.Steal, Cell(3, 3)), PlayerId.One, Cell(2, 3), 1, 1),
      1,
      1,
    )
    greedy(state) shouldBe Candidate(Cell(3, 3), 1, 1)
  }

  it should "avoid a Pitfall when a Pitfall-free candidate exists" in {
    val state = rolled(
      placed(withSpecialCells(six, CellKind.Pitfall, Cell(0, 1)), PlayerId.One, Cell(0, 0), 1, 1),
      1,
      1,
    )
    greedy(state) shouldBe Candidate(Cell(1, 0), 1, 1)
  }

  it should "fall back to denying the opponent's frontier without special cells" in {
    val state = rolled(
      placed(
        placed(GameState.initial(six), PlayerId.One, Cell(2, 2), 1, 1),
        PlayerId.Two,
        Cell(2, 4),
        1,
        1,
      ),
      1,
      1,
    )
    greedy(state) shouldBe Candidate(Cell(2, 3), 1, 1)
  }

  it should "leave the dice untouched when one candidate is clearly best" in {
    val state = rolled(
      placed(withSpecialCells(six, CellKind.Prize, Cell(3, 3)), PlayerId.One, Cell(2, 3), 1, 1),
      1,
      1,
    )
    val (_, after) = Bot.choosePlacement(state, BotDifficulty.Greedy, ScriptedDice.of(0))
    after shouldBe ScriptedDice.of(0)
  }

  private def blocking(state: GameState, draws: Int*): Candidate =
    Bot.choosePlacement(state, BotDifficulty.Blocking, ScriptedDice(draws.toList))._1

  private def facing(state: GameState): GameState =
    placed(placed(state, PlayerId.One, Cell(2, 2), 1, 1), PlayerId.Two, Cell(2, 4), 1, 1)

  "a Blocking placement" should "deny the opponent's frontier" in {
    blocking(rolled(facing(GameState.initial(six)), 1, 1)) shouldBe Candidate(Cell(2, 3), 1, 1)
  }

  it should "capture a Steal cell in the opponent's frontier" in {
    val state = List(
      (PlayerId.One, Cell(2, 2)),
      (PlayerId.One, Cell(4, 2)),
      (PlayerId.Two, Cell(2, 4)),
      (PlayerId.Two, Cell(4, 4)),
    ).foldLeft(withSpecialCells(six, CellKind.Steal, Cell(4, 3))) { case (acc, (who, cell)) =>
      placed(acc, who, cell, 1, 1)
    }
    blocking(rolled(state, 1, 1)) shouldBe Candidate(Cell(4, 3), 1, 1)
  }

  it should "avoid a Pitfall even on the denying cell" in {
    val state = facing(withSpecialCells(six, CellKind.Pitfall, Cell(2, 3)))
    blocking(rolled(state, 1, 1), 0).topLeft should not be Cell(2, 3)
  }

  it should "take a Prize over denying the frontier" in {
    val state = facing(withSpecialCells(six, CellKind.Prize, Cell(1, 2)))
    blocking(rolled(state, 1, 1)) shouldBe Candidate(Cell(1, 2), 1, 1)
  }

  private val sixWild = Rules(boardSize = 6, wildcard = true)

  private def picking(state: GameState, dice: Int*): GameState =
    val picker = rolled(state, dice*)
    picker.turn shouldBe TurnState.ChoosingWildcard
    picker

  private def wildcard(state: GameState, difficulty: BotDifficulty, draws: Int*): Int =
    Bot.chooseWildcardValue(state, difficulty, ScriptedDice(draws.toList))._1

  "a wildcard value" should "be a Basic bot's plain draw" in {
    wildcard(picking(GameState.initial(sixWild), 2, 2, 0), BotDifficulty.Basic, 4) shouldBe 4
  }

  it should "be the Prize-capturing one for Greedy" in {
    val state = placed(
      withSpecialCells(sixWild, CellKind.Prize, Cell(2, 5)),
      PlayerId.One,
      Cell(2, 2),
      1,
      1,
    )
    wildcard(picking(state, 2, 2, 0), BotDifficulty.Greedy) shouldBe 3
  }

  it should "be the Steal-capturing one for Greedy" in {
    val state = placed(
      withSpecialCells(sixWild, CellKind.Steal, Cell(2, 5)),
      PlayerId.One,
      Cell(2, 2),
      1,
      1,
    )
    wildcard(picking(state, 2, 2, 0), BotDifficulty.Greedy) shouldBe 3
  }

  it should "be the frontier-denying one for Blocking" in {
    val state =
      placed(
        placed(GameState.initial(sixWild), PlayerId.One, Cell(0, 0), 1, 1),
        PlayerId.Two,
        Cell(0, 5),
        1,
        1,
      )
    wildcard(picking(state, 1, 1, 0), BotDifficulty.Blocking, 0) shouldBe 4
  }

  it should "be the one with the larger piece for Greedy when no Prize decides" in {
    val state = placed(
      GameState.initial(Rules(boardSize = 8, wildcard = true)),
      PlayerId.One,
      Cell(3, 3),
      1,
      1,
    )
    wildcard(picking(state, 2, 2, 0), BotDifficulty.Greedy) shouldBe 6
  }

  private def rerollRules(size: Int, wildcard: Boolean = false, reroll: Boolean = true): Rules =
    Rules(boardSize = size, wildcard = wildcard, reroll = reroll)

  private def reroll(state: GameState, difficulty: BotDifficulty): Boolean =
    Bot.shouldReroll(state, difficulty)

  private def lone(rules: Rules): GameState =
    placed(GameState.initial(rules), PlayerId.One, Cell(2, 3), 1, 1)

  "a reroll" should "go to Blocking but not Greedy at a plain zero score" in {
    val state = rolled(placed(lone(rerollRules(6)), PlayerId.Two, Cell(5, 5), 1, 1), 1, 1)
    state.turn shouldBe TurnState.ChoosingPlacement
    reroll(state, BotDifficulty.Blocking) shouldBe true
    reroll(state, BotDifficulty.Greedy) shouldBe false
  }

  it should "go to Greedy when a Prize exists but is out of this roll's reach" in {
    val state = rolled(
      placed(
        withSpecialCells(rerollRules(6), CellKind.Prize, Cell(5, 5)),
        PlayerId.One,
        Cell(0, 0),
        1,
        1,
      ),
      1,
      1,
    )
    state.turn shouldBe TurnState.ChoosingPlacement
    reroll(state, BotDifficulty.Greedy) shouldBe true
  }

  it should "go to Greedy when a Steal cell exists but is out of this roll's reach" in {
    val state = rolled(
      placed(
        withSpecialCells(rerollRules(6), CellKind.Steal, Cell(5, 5)),
        PlayerId.One,
        Cell(0, 0),
        1,
        1,
      ),
      1,
      1,
    )
    state.turn shouldBe TurnState.ChoosingPlacement
    reroll(state, BotDifficulty.Greedy) shouldBe true
  }

  it should "go to Greedy when every candidate covers a Pitfall" in {
    val state = rolled(
      placed(
        withSpecialCells(rerollRules(6), CellKind.Pitfall, Cell(0, 1), Cell(1, 0)),
        PlayerId.One,
        Cell(0, 0),
        1,
        1,
      ),
      1,
      1,
    )
    state.turn shouldBe TurnState.ChoosingPlacement
    reroll(state, BotDifficulty.Greedy) shouldBe true
  }

  it should "not happen when rerolls are off, even at a zero score" in {
    reroll(rolled(lone(rerollRules(6, reroll = false)), 1, 1), BotDifficulty.Greedy) shouldBe false
  }

  it should "not happen once the charges are spent" in {
    val fresh = lone(rerollRules(6))
    val spent = fresh.copy(players =
      fresh.players.updated(
        PlayerId.One,
        fresh.players(PlayerId.One).copy(rerollsUsed = Constants.REROLL_LIMIT),
      )
    )
    reroll(rolled(spent, 1, 1), BotDifficulty.Greedy) shouldBe false
  }

  it should "never come from a Basic bot" in {
    reroll(rolled(lone(rerollRules(6)), 1, 1), BotDifficulty.Basic) shouldBe false
  }

  it should "always go to a skipped roll while a charge is left" in {
    val state = rolled(GameState.initial(rerollRules(2)), 6, 6)
    state.turn shouldBe TurnState.Skipped
    reroll(state, BotDifficulty.Greedy) shouldBe true
  }

  it should "go to Greedy when every wildcard value scores zero but a Prize is within reach" in {
    val state =
      rolled(withSpecialCells(rerollRules(6, wildcard = true), CellKind.Prize, Cell(5, 5)), 5, 5, 0)
    state.turn shouldBe TurnState.ChoosingWildcard
    reroll(state, BotDifficulty.Greedy) shouldBe true
  }

  it should "not go to Blocking when the opponent's frontier is out of reach" in {
    reroll(rolled(GameState.initial(rerollRules(6)), 1, 1), BotDifficulty.Blocking) shouldBe false
  }

  it should "not go to Greedy when every Prize is beyond a roll of the start corner" in {
    val state = rolled(withSpecialCells(rerollRules(10), CellKind.Prize, Cell(9, 9)), 1, 1)
    reroll(state, BotDifficulty.Greedy) shouldBe false
  }

  it should "go to Greedy when a Prize is within a roll of the start corner" in {
    val state = rolled(withSpecialCells(rerollRules(10), CellKind.Prize, Cell(5, 5)), 1, 1)
    reroll(state, BotDifficulty.Greedy) shouldBe true
  }

  "a Basic placement" should "be one of the legal candidates" in {
    val state     = rolled(small, 2, 3, 0)
    val (pick, _) = Bot.choosePlacement(state, BotDifficulty.Basic, ScriptedDice.of(0))
    state.legal.getOrElse(Roll(pick.width, pick.height), Set.empty) should contain(pick.topLeft)
  }

  it should "take the candidate its draw indexes, in (row, col, width, height) order" in {
    val state = rolled(small, 2, 3)
    val all = state.legal.toVector.flatMap((roll, cells) =>
      cells.map(Candidate(_, roll.first, roll.second))
    ).sortBy(c => (c.topLeft.row, c.topLeft.col, c.width, c.height))
    val (first, _) = Bot.choosePlacement(state, BotDifficulty.Basic, ScriptedDice.of(0))
    val (last, _)  = Bot.choosePlacement(state, BotDifficulty.Basic, ScriptedDice.of(all.size - 1))
    first shouldBe all.head
    last shouldBe all.last
  }
