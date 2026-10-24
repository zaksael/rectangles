package dev.zaksael.rectangles.server.session

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PendingWildcard
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Placement
import dev.zaksael.rectangles.server.Draw
import dev.zaksael.rectangles.server.ReplayDice
import dev.zaksael.rectangles.server.protocol.ClientMessage
import dev.zaksael.rectangles.server.protocol.ErrorReason

class ActionsSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def dice(values: Int*): ReplayDice = ReplayDice(values.toList.map(Draw.RandInt(1, 6, _)))

  private def play(boardSize: Int = 6, rolls: Seq[Int] = Seq(2, 3)): Play =
    Play(GameState.initial(Rules(boardSize = boardSize)), dice(rolls*))

  "a roll" should "take the roll from the dice" in {
    val rolled = Actions(play(), ClientMessage.Roll).value
    rolled.state.lastRoll shouldBe Some(Roll(2, 3))
    rolled.state.turn shouldBe TurnState.ChoosingPlacement
  }

  it should "be refused as an invalid action when it is not time to roll" in {
    val rolled = Actions(play(rolls = Seq(2, 3, 4, 5)), ClientMessage.Roll).value
    Actions(rolled, ClientMessage.Roll).left.value.reason shouldBe ErrorReason.InvalidAction
  }

  "a placement" should "pass the turn to the other player" in {
    val rolled = Actions(play(), ClientMessage.Roll).value
    val placed = Actions(rolled, ClientMessage.Place(Cell(0, 0), 2, 3)).value
    placed.state.current shouldBe PlayerId.Two
    placed.state.turn shouldBe TurnState.AwaitingRoll
  }

  it should "be refused as illegal when the spot is not allowed" in {
    val rolled = Actions(play(), ClientMessage.Roll).value
    Actions(
      rolled,
      ClientMessage.Place(Cell(3, 3), 2, 3),
    ).left.value.reason shouldBe ErrorReason.IllegalPlacement
  }

  it should "end the game instead of passing the turn when nothing more can be placed" in {
    val rolled = Actions(play(boardSize = 1, rolls = Seq(1, 1)), ClientMessage.Roll).value
    val over   = Actions(rolled, ClientMessage.Place(Cell(0, 0), 1, 1)).value
    over.state.turn shouldBe TurnState.GameOver
    over.state.gameOver shouldBe Some(GameOverReason.BoardFull)
    over.state.current shouldBe PlayerId.One
  }

  /**
   * Player One owns a 3x4 block and a 1x3 column of a 4x4 board: only (3, 3) is left, so a 6 and a
   * 6 cannot be placed.
   */
  private def stuckPlay(): Play =
    val start  = GameState.initial(Rules(boardSize = 4))
    val first  = Placement.place(start.board, start.players(PlayerId.One), Cell(0, 0), 3, 4)
    val second = Placement.place(first.board, first.player, Cell(0, 3), 1, 3)
    Play(
      start.copy(
        board = second.board,
        players = start.players.updated(PlayerId.One, second.player),
      ),
      dice(6, 6),
    )

  "a skip" should "pass the turn after a roll that could not be placed" in {
    val skipped = Actions(stuckPlay(), ClientMessage.Roll).value
    skipped.state.turn shouldBe TurnState.Skipped
    val next = Actions(skipped, ClientMessage.Skip).value
    next.state.current shouldBe PlayerId.Two
    next.state.turn shouldBe TurnState.AwaitingRoll
  }

  it should "be refused as an invalid action when there is nothing to skip" in {
    Actions(play(), ClientMessage.Skip).left.value.reason shouldBe ErrorReason.InvalidAction
    val rolled = Actions(play(), ClientMessage.Roll).value
    Actions(rolled, ClientMessage.Skip).left.value.reason shouldBe ErrorReason.InvalidAction
  }

  "a reroll or a wildcard choice" should "be refused while those rules are off" in {
    val rolled = Actions(play(), ClientMessage.Roll).value
    Actions(rolled, ClientMessage.Reroll).left.value.reason shouldBe ErrorReason.InvalidAction
    Actions(
      rolled,
      ClientMessage.ChooseWildcard(3),
    ).left.value.reason shouldBe ErrorReason.InvalidAction
  }

  "a reroll" should "be refused before any roll" in {
    val open = Play(GameState.initial(Rules(boardSize = 19, reroll = true)), dice())
    Actions(open, ClientMessage.Reroll).left.value.reason shouldBe ErrorReason.InvalidAction
  }

  it should "spend a charge and roll again" in {
    val stuck = GameState.initial(Rules(boardSize = 19, reroll = true)).copy(
      turn = TurnState.Skipped,
      lastRoll = Some(Roll(6, 6)),
    )
    val rerolled = Actions(Play(stuck, dice(2, 3)), ClientMessage.Reroll).value
    rerolled.state.players(PlayerId.One).rerollsUsed shouldBe 1
    rerolled.state.lastRoll shouldBe Some(Roll(2, 3))
  }

  private def picking: Play =
    val open = GameState.initial(Rules(boardSize = 19, wildcard = true)).copy(
      turn = TurnState.ChoosingWildcard,
      lastRoll = Some(Roll(6, 6)),
      wildcard = Some(PendingWildcard(Some(0), Roll(6, 6))),
    )
    Play(open, dice())

  "a wildcard choice" should "be refused outside the picker" in {
    val open = Play(GameState.initial(Rules(boardSize = 19, wildcard = true)), dice())
    Actions(open, ClientMessage.ChooseWildcard(4)).left.value.reason shouldBe
      ErrorReason.InvalidAction
  }

  it should "be refused as an illegal value outside 1 to 6" in {
    Actions(picking, ClientMessage.ChooseWildcard(9)).left.value.reason shouldBe
      ErrorReason.IllegalWildcardValue
  }

  it should "settle the roll with the chosen die" in {
    val chosen = Actions(picking, ClientMessage.ChooseWildcard(1)).value
    chosen.state.lastRoll shouldBe Some(Roll(1, 6))
    Set(TurnState.ChoosingPlacement, TurnState.Skipped) should contain(chosen.state.turn)
  }

  "a surrender" should "end the game with the surrendering player named" in {
    val over = Actions(play(), ClientMessage.Surrender).value
    over.state.turn shouldBe TurnState.GameOver
    over.state.gameOver shouldBe Some(GameOverReason.Surrendered(PlayerId.One))
  }

  it should "change nothing once the game is over" in {
    val over = Actions(play(), ClientMessage.Surrender).value
    Actions(over, ClientMessage.Surrender).value.state shouldBe over.state
  }
