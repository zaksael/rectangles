package dev.zaksael.rectangles.server.protocol

import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Placement
import dev.zaksael.rectangles.rules.Turns

class SerializeSpec extends AnyFlatSpec with Matchers with EitherValues:
  private def game(boardSize: Int = 19): GameState = GameState.initial(Rules(boardSize = boardSize))

  /** The state with a piece put on the board for `who`, without rolling or checking legality. */
  private def placed(
      state: GameState,
      who: PlayerId,
      topLeft: Cell,
      width: Int,
      height: Int,
  ): GameState =
    val result = Placement.place(state.board, state.players(who), topLeft, width, height)
    state.copy(board = result.board, players = state.players.updated(who, result.player))

  private def at(json: Json, path: String*) =
    path.foldLeft(json.hcursor: io.circe.ACursor)(_.downField(_))

  "a serialized player" should "carry its total area and total score" in {
    val json = Serialize.game(placed(game(), PlayerId.One, Cell(0, 0), 3, 4))
    at(json, "players", "1", "score").get[Int]("totalArea").value shouldBe 12
    at(json, "players", "1", "score").get[Int]("totalScore").value shouldBe 12
  }

  it should "carry the area it can still reach and the prize points in that reach" in {
    val withPrize = game(4).copy(board =
      game(4).board.copy(specialCells = Set(SpecialCell(CellKind.Prize, Cell(0, 1), 0)))
    )
    val json      = Serialize.game(placed(withPrize, PlayerId.One, Cell(0, 0), 1, 1))
    val potential = at(json, "players", "1", "score", "potential")
    potential.get[Int]("area").value shouldBe 15
    potential.downField("prize").get[Int]("points").value shouldBe 10
  }

  "the recent turns" should "be empty before any move" in {
    at(Serialize.game(game(11)), "turn").get[List[Json]]("recentTurns").value shouldBe empty
  }

  /**
   * One move for the current player: the roll and its only legal spot are set by hand, then placed.
   */
  private def move(state: GameState, topLeft: Cell, width: Int, height: Int): GameState =
    val roll = Roll(width, height)
    val ready = state.copy(
      lastRoll = Some(roll),
      legal = Map(roll -> Set(topLeft)),
      turn = TurnState.ChoosingPlacement,
    )
    Turns.endTurn(Turns.attemptPlace(ready, topLeft, width, height).value)

  it should "keep the last six, each with the mover's own points" in {
    val moves = List(
      (Cell(0, 0), 1, 1),
      (Cell(10, 10), 1, 1),
      (Cell(1, 0), 1, 2),
      (Cell(9, 10), 1, 1),
      (Cell(3, 0), 1, 3),
      (Cell(6, 10), 1, 3),
      (Cell(6, 0), 1, 1),
    )
    val state             = moves.foldLeft(game(11))((acc, m) => move(acc, m._1, m._2, m._3))
    val recent            = at(Serialize.game(state), "turn").get[List[Json]]("recentTurns").value
    def ints(key: String) = recent.map(_.hcursor.get[Int](key).value)
    ints("playerId") shouldBe List(2, 1, 2, 1, 2, 1)
    ints("points") shouldBe List(1, 2, 1, 3, 3, 1)
    ints("turn") shouldBe List(2, 3, 4, 5, 6, 7)
    recent.last.hcursor.get[Json]("placed").value shouldBe Json.obj(
      "topLeft" -> Json.arr(Json.fromInt(6), Json.fromInt(0)),
      "width"   -> Json.fromInt(1),
      "height"  -> Json.fromInt(1),
    )
    recent.last.hcursor.get[Json]("score").value shouldBe Json.obj(
      "1" -> Json.fromInt(7),
      "2" -> Json.fromInt(5),
    )
  }
