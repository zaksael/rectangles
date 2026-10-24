package dev.zaksael.rectangles.rules

import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.ScoreBreakdown
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.placed
import dev.zaksael.rectangles.withSpecialCells

class ScoringSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(boardSize: Int = 8): GameState = GameState.initial(Rules(boardSize = boardSize))

  "a vanilla score" should "equal the player's area" in {
    val state = placed(game(), PlayerId.One, Cell(0, 0), 2, 2)
    Scoring.total(state, PlayerId.One) shouldBe 4
  }

  "the winner" should "be the player with more area" in {
    val state =
      placed(placed(game(), PlayerId.One, Cell(0, 0), 3, 2), PlayerId.Two, Cell(6, 6), 2, 2)
    Scoring.winner(state) shouldBe Some(PlayerId.One)
  }

  it should "be nobody when the areas tie" in {
    val state =
      placed(placed(game(), PlayerId.One, Cell(0, 0), 2, 2), PlayerId.Two, Cell(6, 6), 2, 2)
    Scoring.winner(state) shouldBe None
  }

  "the breakdown history" should "show a plain placement as area for the mover only" in {
    val (rolled, _) = Turns.rollDice(game(6), ScriptedDice.of(2, 3)).value
    val state       = Turns.attemptPlace(rolled, Cell(0, 0), 2, 3).value
    Scoring.breakdownHistory(state) shouldBe Vector(
      Map(PlayerId.One -> ScoreBreakdown(area = 6), PlayerId.Two -> ScoreBreakdown())
    )
  }

  "the potential history" should "end at each player's live potential" in {
    val state =
      placed(placed(game(6), PlayerId.One, Cell(0, 0), 2, 3), PlayerId.Two, Cell(5, 5), 1, 1)
    val played = state.copy(history =
      Vector(
        TurnRecord(PlayerId.One, Roll(2, 3), Some(Rectangle(Cell(0, 0), 2, 3, PlayerId.One))),
        TurnRecord(PlayerId.Two, Roll(1, 1), Some(Rectangle(Cell(5, 5), 1, 1, PlayerId.Two))),
      )
    )
    val live = state.players.view.mapValues(Scoring.potential(state.board, _)).toMap
    live shouldBe Map(PlayerId.One -> Potential(29, 0), PlayerId.Two -> Potential(29, 0))
    Scoring.potentialHistory(played).lastOption shouldBe Some(live)
  }

  private def capturedPrizes(state: GameState, who: PlayerId, count: Int): GameState =
    state.copy(players =
      state.players.updated(
        who,
        state.players(who).copy(specialCaptures = Map(CellKind.Prize -> count)),
      )
    )

  "the total score" should "decide a winner that area alone would not" in {
    val state = capturedPrizes(
      placed(placed(game(), PlayerId.One, Cell(0, 0), 5, 2), PlayerId.Two, Cell(6, 4), 4, 2),
      PlayerId.Two,
      1,
    )
    state.players(PlayerId.One).totalArea should be > state.players(PlayerId.Two).totalArea
    Scoring.winner(state) shouldBe Some(PlayerId.Two)
  }

  "a surrender" should "give the win to the opponent whatever the prize bonus" in {
    val state = capturedPrizes(placed(game(), PlayerId.One, Cell(0, 0), 5, 5), PlayerId.One, 3)
    Scoring.winner(Turns.surrender(state)) shouldBe Some(PlayerId.Two)
  }

  "a player's potential" should "hold the open cells it can reach and the prize points among them" in {
    val state = placed(
      withSpecialCells(Rules(boardSize = 4), CellKind.Prize, Cell(0, 1), Cell(3, 2)),
      PlayerId.One,
      Cell(0, 0),
      1,
      1,
    )
    Scoring.potential(state.board, state.players(PlayerId.One)) shouldBe Potential(15, 20)
  }

  it should "leave out a prize already captured" in {
    val state = placed(
      withSpecialCells(Rules(boardSize = 4), CellKind.Prize, Cell(0, 1)),
      PlayerId.One,
      Cell(0, 0),
      2,
      1,
    )
    Scoring.potential(state.board, state.players(PlayerId.One)).prizePoints shouldBe 0
  }

  "the breakdown history" should "credit a prize to the capturer only" in {
    val (rolled, _) = Turns.rollDice(
      withSpecialCells(Rules(boardSize = 11), CellKind.Prize, Cell(0, 0)),
      ScriptedDice.of(2, 2),
    ).value
    val state = Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value
    Scoring.breakdownHistory(state) shouldBe Vector(
      Map(
        PlayerId.One -> ScoreBreakdown(area = 4, prize = 10),
        PlayerId.Two -> ScoreBreakdown(),
      )
    )
  }

  it should "end at the live breakdown of both players" in {
    val (rolled, _) = Turns.rollDice(
      withSpecialCells(Rules(boardSize = 11), CellKind.Prize, Cell(5, 5)),
      ScriptedDice.of(6, 6),
    ).value
    val state = Turns.attemptPlace(rolled, Cell(0, 0), 6, 6).value
    Scoring.breakdownHistory(state).lastOption shouldBe Some(
      Map(
        PlayerId.One -> Scoring.breakdown(state, PlayerId.One),
        PlayerId.Two -> Scoring.breakdown(state, PlayerId.Two),
      )
    )
    Scoring.breakdown(state, PlayerId.One).prize shouldBe 10
  }

  "the potential history" should "count a prize both players can still reach" in {
    val (rolled, _) = Turns.rollDice(
      withSpecialCells(Rules(boardSize = 11), CellKind.Prize, Cell(5, 5)),
      ScriptedDice.of(2, 2),
    ).value
    val state = Turns.attemptPlace(rolled, Cell(0, 0), 2, 2).value
    Scoring.potentialHistory(state).map(step =>
      PlayerId.values.toList.map(step(_).prizePoints)
    ) shouldBe
      Vector(List(10, 10))
  }
