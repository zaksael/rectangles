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
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.placed

class ComebackSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(size: Int, nudge: Boolean = true, reroll: Boolean = false): GameState =
    GameState.initial(Rules(boardSize = size, comebackNudge = nudge, reroll = reroll))

  private def granted(state: GameState, who: PlayerId): GameState =
    state.copy(players =
      state.players.updated(who, state.players(who).copy(comebackNudgeGranted = true))
    )

  private def nudged(state: GameState, who: PlayerId): Boolean =
    state.players(who).comebackNudgeGranted

  "the comeback threshold" should "scale with the board size" in {
    Rerolls.comebackThreshold(19) shouldBe 29
    Rerolls.comebackThreshold(23) shouldBe 43
    Rerolls.comebackThreshold(27) shouldBe 59
  }

  "a placement that opens a gap of the threshold" should "grant the trailing player only" in {
    val behind      = placed(game(4), PlayerId.Two, Cell(3, 0), 3, 1)
    val (rolled, _) = Turns.rollDice(behind, ScriptedDice.of(1, 1)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 1, 1).value
    nudged(state, PlayerId.One) shouldBe true
    nudged(state, PlayerId.Two) shouldBe false
  }

  it should "grant nobody with the rule off" in {
    val behind      = placed(game(4, nudge = false), PlayerId.Two, Cell(3, 0), 3, 1)
    val (rolled, _) = Turns.rollDice(behind, ScriptedDice.of(1, 1)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 1, 1).value
    nudged(state, PlayerId.One) shouldBe false
  }

  it should "count a captured prize, not only area" in {
    val start = game(11)
    val prized = start.copy(board =
      start.board.copy(specialCells = Set(SpecialCell(CellKind.Prize, Cell(0, 0), 0)))
    )
    val (rolled, _) = Turns.rollDice(prized, ScriptedDice.of(1, 1)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 1, 1).value
    nudged(state, PlayerId.Two) shouldBe true
    nudged(state, PlayerId.One) shouldBe false
  }

  "a grant" should "last, and a gap under the threshold grants nobody" in {
    val state = Rerolls.maybeGrantNudge(granted(
      placed(game(4), PlayerId.One, Cell(0, 0), 1, 1),
      PlayerId.One,
    ))
    nudged(state, PlayerId.One) shouldBe true
    nudged(state, PlayerId.Two) shouldBe false
  }

  "a granted player" should "be able to reroll even with the reroll rule off" in {
    val state = granted(game(6), PlayerId.One)
    Rerolls.canReroll(state) shouldBe true
  }

  "the reroll limit" should "gain the nudge charge once granted" in {
    val plain = game(6, reroll = true)
    Rerolls.limit(plain.rules, plain.players(PlayerId.One)) shouldBe Constants.REROLL_LIMIT
    val bumped = granted(plain, PlayerId.One)
    Rerolls.limit(bumped.rules, bumped.players(PlayerId.One)) shouldBe Constants.REROLL_LIMIT + 1
  }

  it should "be a single charge when only the nudge grants one" in {
    val state = granted(game(6), PlayerId.One)
    Rerolls.limit(state.rules, state.players(PlayerId.One)) shouldBe 1
    val spent = state.copy(players =
      state.players.updated(PlayerId.One, state.players(PlayerId.One).copy(rerollsUsed = 1))
    )
    Rerolls.canReroll(spent) shouldBe false
  }
