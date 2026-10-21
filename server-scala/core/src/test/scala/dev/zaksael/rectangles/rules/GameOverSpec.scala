package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.placed

class GameOverSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(boardSize: Int, skipLimit: Int = 5): GameState =
    GameState.initial(Rules(boardSize = boardSize, skipLimit = skipLimit))

  "a 2x2 game" should "end with the board full when the last cell is placed" in {
    def oneByOne(at: Cell) = Some((at, 1, 1))
    val dice               = ScriptedDice.of(1, 1, 1, 1, 1, 1, 1, 1)
    val (first, d1)        = turn(game(2), dice, oneByOne(Cell(0, 0)))
    val (second, d2)       = turn(first, d1, oneByOne(Cell(1, 1)))
    val (third, d3)        = turn(second, d2, oneByOne(Cell(0, 1)))
    val (fourth, _)        = turn(third, d3, oneByOne(Cell(1, 0)))
    Seq(first, second, third).map(_.turn) should not contain TurnState.GameOver
    fourth.turn shouldBe TurnState.GameOver
    fourth.gameOver shouldBe Some(GameOverReason.BoardFull)
  }

  "a roll on a full board" should "skip and end the game" in {
    val full =
      placed(placed(game(2), PlayerId.One, Cell(0, 0), 1, 2), PlayerId.Two, Cell(0, 1), 1, 2)
    val (skipped, _) = Turns.rollDice(full, ScriptedDice.of(3, 3)).value
    skipped.turn shouldBe TurnState.Skipped
    Turns.checkGameOver(skipped).turn shouldBe TurnState.GameOver
  }

  "a player with no empty cell beside their piece" should "end the game as blocked" in {
    val boxedIn = placed(
      placed(placed(game(4), PlayerId.One, Cell(0, 0), 1, 1), PlayerId.Two, Cell(1, 0), 1, 1),
      PlayerId.Two,
      Cell(0, 1),
      1,
      1,
    )
    val over = Turns.checkGameOver(boxedIn)
    over.turn shouldBe TurnState.GameOver
    over.gameOver shouldBe Some(GameOverReason.PlayerBlocked(PlayerId.One))
  }

  "a player who has not moved yet" should "not count as blocked" in {
    val onlyTwoMoved = placed(game(4), PlayerId.Two, Cell(3, 3), 1, 1)
    Turns.checkGameOver(onlyTwoMoved).turn should not be TurnState.GameOver
  }

  /** Both players have a piece in their corner; Player One has skipped `skips` turns in a row. */
  private def withSkips(skipLimit: Int, skips: Int): GameState =
    val state = placed(
      placed(game(8, skipLimit), PlayerId.One, Cell(0, 0), 1, 1),
      PlayerId.Two,
      Cell(7, 7),
      1,
      1,
    )
    state.copy(players =
      state.players.updated(
        PlayerId.One,
        state.players(PlayerId.One).copy(consecutiveSkips = skips),
      )
    )

  "a player at the skip limit" should "end the game" in {
    val over = Turns.checkGameOver(withSkips(skipLimit = 3, skips = 3))
    over.turn shouldBe TurnState.GameOver
    over.gameOver shouldBe Some(GameOverReason.SkipLimit(PlayerId.One))
  }

  it should "not end the game one skip short of the limit" in {
    Turns.checkGameOver(withSkips(skipLimit = 3, skips = 2)).turn should not be TurnState.GameOver
  }

  it should "follow the limit the rules set" in {
    Turns.checkGameOver(withSkips(skipLimit = 1, skips = 1)).gameOver shouldBe
      Some(GameOverReason.SkipLimit(PlayerId.One))
  }

  "a 1x1 board" should "end after the first placement with that player winning" in {
    val (rolled, _) = Turns.rollDice(game(1), ScriptedDice.of(1, 1)).value
    val over        = Turns.checkGameOver(Turns.attemptPlace(rolled, Cell(0, 0), 1, 1).value)
    over.turn shouldBe TurnState.GameOver
    Scoring.winner(over) shouldBe Some(PlayerId.One)
  }

  "surrendering" should "end the game and give the win to the opponent despite less area" in {
    val state =
      placed(placed(game(8), PlayerId.One, Cell(0, 0), 5, 5), PlayerId.Two, Cell(7, 7), 1, 1)
    val over = Turns.surrender(state)
    over.turn shouldBe TurnState.GameOver
    over.gameOver shouldBe Some(GameOverReason.Surrendered(PlayerId.One))
    Scoring.winner(over) shouldBe Some(PlayerId.Two)
  }

  it should "change nothing once the game is over" in {
    val over = Turns.checkGameOver(placed(game(1), PlayerId.One, Cell(0, 0), 1, 1))
    Turns.surrender(over) shouldBe over
  }

  "a placement" should "reset the mover's skip streak" in {
    val streaking = game(4).copy(players =
      game(4).players.updated(
        PlayerId.One,
        game(4).players(PlayerId.One).copy(consecutiveSkips = 2),
      )
    )
    val (rolled, _)  = Turns.rollDice(streaking, ScriptedDice.of(2, 2)).value
    val afterPlacing = Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value
    afterPlacing.players(PlayerId.One).consecutiveSkips shouldBe 0
  }

  /**
   * Roll, then place `piece` (top-left, width, height) if given; check for game over and pass the
   * turn unless over.
   */
  private def turn(
      state: GameState,
      dice: Dice,
      piece: Option[(Cell, Int, Int)] = None,
  ): (GameState, Dice) =
    val (rolled, rest) = Turns.rollDice(state, dice).value
    val moved   = piece.fold(rolled)((at, w, h) => Turns.attemptPlace(rolled, at, w, h).value)
    val checked = Turns.checkGameOver(moved)
    (if checked.turn == TurnState.GameOver then checked else Turns.endTurn(checked), rest)

  "repeated skips" should "reach the skip limit for the player who keeps skipping" in {
    val almostFull = placed(
      placed(game(4, skipLimit = 2), PlayerId.One, Cell(0, 0), 3, 4),
      PlayerId.One,
      Cell(0, 3),
      1,
      3,
    )
    val dice         = ScriptedDice.of(6, 6, 6, 6, 6, 6)
    val (first, d1)  = turn(almostFull, dice)
    val (second, d2) = turn(first, d1)
    val (third, _)   = turn(second, d2)
    first.players(PlayerId.One).consecutiveSkips shouldBe 1
    second.players(PlayerId.One).consecutiveSkips shouldBe 1
    third.gameOver shouldBe Some(GameOverReason.SkipLimit(PlayerId.One))
  }

  "a skip streak" should "belong to the player who skipped" in {
    // Player Two's start corner is taken, so every roll of theirs is a skip.
    val blockedTwo = placed(game(4, skipLimit = 2), PlayerId.One, Cell(3, 3), 1, 1)
    val dice       = ScriptedDice.of(1, 2, 3, 5, 2, 1, 1, 3)
    val (t1, d1)   = turn(blockedTwo, dice, Some((Cell(1, 3), 1, 2)))
    val (t2, d2)   = turn(t1, d1)
    val (t3, d3)   = turn(t2, d2, Some((Cell(1, 1), 2, 1)))
    val (t4, _)    = turn(t3, d3)
    t2.players(PlayerId.Two).consecutiveSkips shouldBe 1
    t3.players(PlayerId.One).consecutiveSkips shouldBe 0
    t4.players(PlayerId.One).consecutiveSkips shouldBe 0
    t4.gameOver shouldBe Some(GameOverReason.SkipLimit(PlayerId.Two))
  }

  "a new game" should "have no reason, roll, legal moves, history or skips" in {
    val fresh = GameState.initial(Rules(boardSize = 4))
    fresh.gameOver shouldBe None
    fresh.lastRoll shouldBe None
    fresh.legal shouldBe empty
    fresh.history shouldBe empty
    fresh.players.values.map(_.consecutiveSkips) should contain only 0
    fresh.players.values.flatMap(_.pieces) shouldBe empty
  }
