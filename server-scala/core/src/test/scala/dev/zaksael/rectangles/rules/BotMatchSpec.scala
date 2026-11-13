package dev.zaksael.rectangles.rules

import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PendingWildcard
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.Seats
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.placed

class BotMatchSpec extends AnyFlatSpec with Matchers with OptionValues:
  private val small   = Rules(boardSize = 6)
  private val greedy  = Seats(BotDifficulty.Greedy, BotDifficulty.Greedy)
  private val rerolls = Rules(boardSize = 19, reroll = true)

  /** Player Two to move, part-way through a turn the test sets up by hand. */
  private def midTurn(
      rules: Rules,
      turn: TurnState,
      roll: Roll,
      legal: Map[Roll, Set[Cell]] = Map.empty,
      wildcard: Option[PendingWildcard] = None,
  ): GameState =
    GameState.initial(rules, PlayerId.Two).copy(
      turn = turn,
      lastRoll = Some(roll),
      legal = legal,
      wildcard = wildcard,
    )

  private def stepped(state: GameState, difficulty: BotDifficulty, rolls: Int*): GameState =
    BotMatch.step(state, difficulty, ScriptedDice.of(rolls*)).value._1

  private def twoUsed(state: GameState) = state.players(PlayerId.Two).rerollsUsed

  "a bot step on a skipped roll" should "reroll instead of confirming the skip" in {
    val after =
      stepped(midTurn(rerolls, TurnState.Skipped, Roll(6, 6)), BotDifficulty.Blocking, 2, 3)
    twoUsed(after) shouldBe 1
    after.history shouldBe empty
  }

  "a bot step on a bad placement roll" should "reroll instead of placing" in {
    val state = placed(
      midTurn(rerolls, TurnState.ChoosingPlacement, Roll(1, 1), Map(Roll(1, 1) -> Set(Cell(5, 5)))),
      PlayerId.One,
      Cell(14, 18),
      1,
      1,
    )
    val after = stepped(state, BotDifficulty.Blocking, 2, 3)
    twoUsed(after) shouldBe 1
    after.players(PlayerId.Two).pieces shouldBe empty
  }

  "a bot step in the wildcard picker" should "reroll when every value covers a Pitfall" in {
    val picker = placed(
      midTurn(
        rerolls,
        TurnState.ChoosingWildcard,
        Roll(6, 6),
        wildcard = Some(PendingWildcard(Some(0), Roll(6, 6))),
      ),
      PlayerId.Two,
      Cell(18, 18),
      1,
      1,
    )
    val state = picker.copy(board =
      picker.board.copy(specialCells =
        Set(
          SpecialCell(CellKind.Pitfall, Cell(17, 18)),
          SpecialCell(CellKind.Pitfall, Cell(18, 17)),
        )
      )
    )
    twoUsed(stepped(state, BotDifficulty.Greedy, 2, 3)) shouldBe 1
  }

  it should "pick a value when it is not rerolling" in {
    val state = midTurn(
      Rules(boardSize = 19, wildcard = true),
      TurnState.ChoosingWildcard,
      Roll(6, 6),
      wildcard = Some(PendingWildcard(Some(0), Roll(6, 6))),
    )
    stepped(state, BotDifficulty.Basic, 3).turn should not be TurnState.ChoosingWildcard
  }

  "a bot step on a finished game" should "decline" in {
    val over = midTurn(Rules(), TurnState.GameOver, Roll(1, 1))
    BotMatch.step(over, BotDifficulty.Basic, ScriptedDice.of()) shouldBe None
  }

  "a bot match" should "play to the end and score both seats" in {
    val result = BotMatch.play(small, greedy, Some(PlayerId.One), SplitMix64(1L)).value

    result.scores.values.forall(_ > 0) shouldBe true
  }

  it should "give the same result for the same seed" in {
    val play = () => BotMatch.play(small, greedy, Some(PlayerId.One), SplitMix64(7L))

    play() shouldBe play()
  }

  it should "play each seat at its own difficulty" in {
    val blockingWins = (1L to 30L).count { seed =>
      val blockingSeat = if seed % 2 == 0 then PlayerId.One else PlayerId.Two
      val seats = Seats(
        BotDifficulty.Basic,
        BotDifficulty.Basic,
      ).updated(blockingSeat, BotDifficulty.Blocking)
      BotMatch.play(
        small,
        seats,
        Some(PlayerId.One),
        SplitMix64(seed),
      ).value.winner.contains(blockingSeat)
    }

    blockingWins should be >= 20
  }
