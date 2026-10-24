package dev.zaksael.rectangles.server.session

import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PendingWildcard
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Placement
import dev.zaksael.rectangles.server.Draw
import dev.zaksael.rectangles.server.ReplayDice

class BotTurnsSpec extends AnyFlatSpec with Matchers with OptionValues:
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

  private def withPiece(state: GameState, who: PlayerId, at: Cell): GameState =
    val result = Placement.place(state.board, state.players(who), at, 1, 1)
    state.copy(board = result.board, players = state.players.updated(who, result.player))

  private def dice(rolls: Int*) = ReplayDice(rolls.toList.map(Draw.RandInt(1, 6, _)))

  private def stepped(state: GameState, difficulty: BotDifficulty, rolls: Int*): GameState =
    BotTurns.step(Play(state, dice(rolls*)), difficulty).value.state

  private def twoUsed(state: GameState) = state.players(PlayerId.Two).rerollsUsed

  "a bot step on a skipped roll" should "reroll instead of confirming the skip" in {
    val after =
      stepped(midTurn(rerolls, TurnState.Skipped, Roll(6, 6)), BotDifficulty.Blocking, 2, 3)
    twoUsed(after) shouldBe 1
    after.history shouldBe empty
  }

  "a bot step on a bad placement roll" should "reroll instead of placing" in {
    val state = withPiece(
      midTurn(rerolls, TurnState.ChoosingPlacement, Roll(1, 1), Map(Roll(1, 1) -> Set(Cell(5, 5)))),
      PlayerId.One,
      Cell(14, 18),
    )
    val after = stepped(state, BotDifficulty.Blocking, 2, 3)
    twoUsed(after) shouldBe 1
    after.players(PlayerId.Two).pieces shouldBe empty
  }

  "a bot step in the wildcard picker" should "reroll when every value covers a Pitfall" in {
    val picker = withPiece(
      midTurn(
        rerolls,
        TurnState.ChoosingWildcard,
        Roll(6, 6),
        wildcard = Some(PendingWildcard(Some(0), Roll(6, 6))),
      ),
      PlayerId.Two,
      Cell(18, 18),
    )
    val state = picker.copy(board =
      picker.board.copy(specialCells =
        Set(
          SpecialCell(CellKind.Pitfall, Cell(17, 18), 0),
          SpecialCell(CellKind.Pitfall, Cell(18, 17), 1),
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
    BotTurns.step(Play(over, dice()), BotDifficulty.Basic) shouldBe None
  }
