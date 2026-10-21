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
import dev.zaksael.rectangles.domain.ScoreBreakdown
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.placed

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
    live shouldBe Map(PlayerId.One -> Potential(29), PlayerId.Two -> Potential(29))
    Scoring.potentialHistory(played).lastOption shouldBe Some(live)
  }
