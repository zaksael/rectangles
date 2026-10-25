package dev.zaksael.rectangles.server.protocol

import io.circe.Json
import io.circe.parser.parse
import org.scalatest.EitherValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PendingWildcard
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Analysis
import dev.zaksael.rectangles.rules.Placement
import dev.zaksael.rectangles.rules.Series
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

  it should "carry the prizes it has captured" in {
    val base = game()
    val state = base.copy(players =
      base.players.updated(
        PlayerId.One,
        base.players(PlayerId.One).copy(specialCaptures = Map(CellKind.Prize -> 2)),
      )
    )
    at(Serialize.game(state), "players", "1", "houseRules", "prize").focus shouldBe
      Some(parse("""{"captured": 2}""").value)
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

  "the game-over history" should "be null while playing and a list of steps once the game is over" in {
    val playing = move(game(11), Cell(0, 0), 2, 3)
    at(Serialize.game(playing), "gameOver").get[Json]("history").value shouldBe Json.Null

    val expected = parse(
      """[{"playerId":1,"roll":[2,3],"placed":{"topLeft":[0,0],"width":2,"height":3},
        |"wildcardOriginalRoll":null,"score":{"1":6,"2":0},
        |"breakdown":{"1":{"area":6,"prize":0,"pitfall":0,"steal":0,"enclosure":0},
        |"2":{"area":0,"prize":0,"pitfall":0,"steal":0,"enclosure":0}},
        |"potential":{"1":{"area":115,"prize":{"points":0}},"2":{"area":115,"prize":{"points":0}}}}]""".stripMargin
    ).value
    at(
      Serialize.game(Turns.surrender(playing)),
      "gameOver",
    ).get[Json]("history").value shouldBe expected
  }

  private def gameOver(state: GameState) = at(Serialize.game(state), "gameOver")

  "the game-over block" should "name a surrender, who surrendered and the opponent as winner" in {
    val over = Turns.surrender(placed(game(8), PlayerId.One, Cell(0, 0), 5, 5))
    gameOver(over).get[String]("reason").value shouldBe "surrender"
    gameOver(over).get[Int]("playerId").value shouldBe 1
    gameOver(over).get[Int]("winner").value shouldBe 2
  }

  it should "name the skip limit and the player who reached it" in {
    val skipping =
      placed(placed(game(8), PlayerId.One, Cell(0, 0), 1, 1), PlayerId.Two, Cell(7, 7), 1, 1)
    val streak = skipping.copy(players =
      skipping.players.updated(
        PlayerId.One,
        skipping.players(PlayerId.One).copy(consecutiveSkips = 5),
      )
    )
    val over = Turns.checkGameOver(streak)
    gameOver(over).get[String]("reason").value shouldBe "skipLimit"
    gameOver(over).get[Int]("playerId").value shouldBe 1
  }

  it should "name a boxed-in player" in {
    val boxedIn = placed(
      placed(placed(game(4), PlayerId.One, Cell(0, 0), 1, 1), PlayerId.Two, Cell(1, 0), 1, 1),
      PlayerId.Two,
      Cell(0, 1),
      1,
      1,
    )
    val over = Turns.checkGameOver(boxedIn)
    gameOver(over).get[String]("reason").value shouldBe "playerBlocked"
    gameOver(over).get[Int]("playerId").value shouldBe 1
  }

  it should "have no player for a full board, and the larger area as winner" in {
    val over = Turns.checkGameOver(placed(game(1), PlayerId.One, Cell(0, 0), 1, 1))
    gameOver(over).get[String]("reason").value shouldBe "boardFull"
    gameOver(over).get[Json]("playerId").value shouldBe Json.Null
    gameOver(over).get[Int]("winner").value shouldBe 1
  }

  it should "have no winner for a tie, and none while the game is on" in {
    val tied =
      placed(placed(game(2), PlayerId.One, Cell(0, 0), 1, 2), PlayerId.Two, Cell(0, 1), 1, 2)
    gameOver(Turns.checkGameOver(tied)).get[Json]("winner").value shouldBe Json.Null
    gameOver(game(8)).get[Json]("winner").value shouldBe Json.Null
  }

  "the walls section" should "carry the flag and each edge as its two sorted cells" in {
    val walled = GameState.initial(Rules(walls = true)).copy(board =
      Board(wallEdges =
        Set(Edge.between(Cell(5, 6), Cell(5, 5)), Edge.between(Cell(1, 0), Cell(0, 0)))
      )
    )
    val walls = at(Serialize.game(walled), "houseRules", "walls")
    walls.get[Boolean]("enabled").value shouldBe true
    walls.get[List[List[List[Int]]]]("edges").value shouldBe
      List(List(List(0, 0), List(1, 0)), List(List(5, 5), List(5, 6)))
  }

  it should "be off with no edges by default" in {
    at(Serialize.game(game()), "houseRules", "walls").focus shouldBe
      Some(parse("""{"enabled": false, "edges": []}""").value)
  }

  "the obstacles section" should "carry the flag and its cells sorted by row then column" in {
    val blocked = GameState.initial(Rules(obstacles = true)).copy(board =
      Board(obstacleCells = Set(Cell(9, 9), Cell(3, 4), Cell(3, 2)))
    )
    val obstacles = at(Serialize.game(blocked), "houseRules", "obstacles")
    obstacles.get[Boolean]("enabled").value shouldBe true
    obstacles.get[List[List[Int]]]("cells").value shouldBe List(List(3, 2), List(3, 4), List(9, 9))
  }

  it should "be off with no cells by default" in {
    at(Serialize.game(game()), "houseRules", "obstacles").focus shouldBe
      Some(parse("""{"enabled": false, "cells": []}""").value)
  }

  "the prize section" should "carry the flag, every prize cell sorted and the points" in {
    val prized = GameState.initial(Rules(prize = true)).copy(board =
      Board(specialCells =
        Set(
          SpecialCell(CellKind.Prize, Cell(9, 9), 0),
          SpecialCell(CellKind.Prize, Cell(3, 4), 1),
          SpecialCell(CellKind.Pitfall, Cell(1, 1), 2),
        )
      )
    )
    val prize = at(Serialize.game(prized), "houseRules", "prize")
    prize.get[Boolean]("enabled").value shouldBe true
    prize.get[List[List[Int]]]("cells").value shouldBe List(List(3, 4), List(9, 9))
    prize.get[Int]("points").value shouldBe 10
  }

  it should "be off with no cells and the default points by default" in {
    at(Serialize.game(game()), "houseRules", "prize").focus shouldBe
      Some(parse("""{"enabled": false, "cells": [], "points": 10}""").value)
  }

  "the pitfall section" should "carry the flag, its cells sorted and the penalty points" in {
    val pitted = GameState.initial(Rules(pitfall = true)).copy(board =
      Board(specialCells =
        Set(
          SpecialCell(CellKind.Pitfall, Cell(9, 9), 0),
          SpecialCell(CellKind.Pitfall, Cell(3, 4), 1),
          SpecialCell(CellKind.Prize, Cell(1, 1), 2),
        )
      )
    )
    val pitfall = at(Serialize.game(pitted), "houseRules", "pitfall")
    pitfall.get[Boolean]("enabled").value shouldBe true
    pitfall.get[List[List[Int]]]("cells").value shouldBe List(List(3, 4), List(9, 9))
    pitfall.get[Int]("points").value shouldBe 10
  }

  it should "be off with no cells by default" in {
    at(Serialize.game(game()), "houseRules", "pitfall").focus shouldBe
      Some(parse("""{"enabled": false, "cells": [], "points": 10}""").value)
  }

  it should "count the pitfalls a player has captured" in {
    val base = game()
    val state = base.copy(players =
      base.players.updated(
        PlayerId.One,
        base.players(PlayerId.One).copy(specialCaptures = Map(CellKind.Pitfall -> 3)),
      )
    )
    at(Serialize.game(state), "players", "1", "houseRules", "pitfall").focus shouldBe
      Some(parse("""{"captured": 3}""").value)
  }

  "the steal section" should "carry the flag, its cells sorted and the steal points" in {
    val stolen = GameState.initial(Rules(steal = true)).copy(board =
      Board(specialCells =
        Set(
          SpecialCell(CellKind.Steal, Cell(9, 9), 0),
          SpecialCell(CellKind.Steal, Cell(3, 4), 1),
          SpecialCell(CellKind.Pitfall, Cell(1, 1), 2),
        )
      )
    )
    val steal = at(Serialize.game(stolen), "houseRules", "steal")
    steal.get[Boolean]("enabled").value shouldBe true
    steal.get[List[List[Int]]]("cells").value shouldBe List(List(3, 4), List(9, 9))
    steal.get[Int]("points").value shouldBe 10
  }

  it should "be off with no cells by default" in {
    at(Serialize.game(game()), "houseRules", "steal").focus shouldBe
      Some(parse("""{"enabled": false, "cells": [], "points": 10}""").value)
  }

  it should "count the steals a player has captured" in {
    val base = game()
    val state = base.copy(players =
      base.players.updated(
        PlayerId.One,
        base.players(PlayerId.One).copy(specialCaptures = Map(CellKind.Steal -> 1)),
      )
    )
    at(Serialize.game(state), "players", "1", "houseRules", "steal").focus shouldBe
      Some(parse("""{"captured": 1}""").value)
  }

  private def stealAtCorner: GameState =
    val state = GameState.initial(Rules(boardSize = 11, steal = true, prize = true, pitfall = true))
    state.copy(board =
      state.board.copy(specialCells = Set(SpecialCell(CellKind.Steal, Cell(0, 0), 0)))
    )

  "the game-over history" should "carry a steal, its parts summing to the score" in {
    val over  = Turns.surrender(move(stealAtCorner, Cell(0, 0), 2, 2))
    val entry = at(Serialize.game(over), "gameOver", "history").downArray
    val parts = entry.downField("breakdown")
    parts.downField("1").get[Int]("steal").value shouldBe 10
    parts.downField("2").get[Int]("steal").value shouldBe -10
    for who <- List("1", "2") do
      parts.downField(who).as[Map[String, Int]].value.values.sum shouldBe
        entry.downField("score").get[Int](who).value
  }

  "a player's score breakdown" should "sum to the total score with every rule on" in {
    val json = Serialize.game(move(stealAtCorner, Cell(0, 0), 2, 2))
    at(json, "players", "1", "score").downField("breakdown").focus shouldBe Some(
      parse("""{"area": 4, "prize": 0, "pitfall": 0, "steal": 10, "enclosure": 0}""").value
    )
    at(json, "players", "2", "score").downField("breakdown").get[Int]("steal").value shouldBe -10
    for who <- List("1", "2") do
      val score = at(json, "players", who, "score")
      score.downField("breakdown").as[Map[String, Int]].value.values.sum shouldBe
        score.get[Int]("totalScore").value
  }

  "the self-enclosed penalty section" should "carry the flag" in {
    at(
      Serialize.game(GameState.initial(Rules(selfEnclosedPenalty = true))),
      "houseRules",
      "selfEnclosedPenalty",
    )
      .focus shouldBe Some(parse("""{"enabled": true}""").value)
  }

  it should "give each player the cells only they enclose" in {
    val ring = List(Cell(1, 2), Cell(3, 2), Cell(2, 1), Cell(2, 3))
    val walled = ring.foldLeft(GameState.initial(Rules(boardSize = 6, selfEnclosedPenalty = true))) {
      (state, topLeft) => placed(state, PlayerId.One, topLeft, 1, 1)
    }
    val state = placed(walled, PlayerId.Two, Cell(5, 5), 1, 1)
    at(Serialize.game(state), "players", "1", "houseRules", "selfEnclosedPenalty").focus shouldBe
      Some(parse("""{"cells": 1}""").value)
  }

  "the reroll section" should "carry the flag and whether a reroll can be spent" in {
    at(
      Serialize.game(GameState.initial(Rules(reroll = true))),
      "houseRules",
      "reroll",
    ).focus shouldBe
      Some(parse("""{"enabled": true, "canReroll": true}""").value)
  }

  it should "give each player the charges used and the limit" in {
    val base = GameState.initial(Rules(reroll = true))
    val used = base.copy(players =
      base.players.updated(PlayerId.One, base.players(PlayerId.One).copy(rerollsUsed = 1))
    )
    at(Serialize.game(used), "players", "1", "houseRules", "reroll").focus shouldBe
      Some(parse("""{"used": 1, "limit": 2}""").value)
  }

  "the comeback nudge section" should "carry the flag" in {
    at(
      Serialize.game(GameState.initial(Rules(comebackNudge = true))),
      "houseRules",
      "comebackNudge",
    )
      .focus shouldBe Some(parse("""{"enabled": true}""").value)
  }

  "a player's reroll limit" should "gain the comeback nudge charge once granted" in {
    val base = GameState.initial(Rules(reroll = true, comebackNudge = true))
    val state = base.copy(players =
      base.players.updated(
        PlayerId.One,
        base.players(PlayerId.One).copy(comebackNudgeGranted = true),
      )
    )
    at(
      Serialize.game(state),
      "players",
      "1",
      "houseRules",
      "reroll",
    ).get[Int]("limit").value shouldBe 3
  }

  "the wildcard section" should "be off with nothing to pick by default" in {
    at(Serialize.game(game()), "houseRules", "wildcard").focus shouldBe Some(
      parse(
        """{"enabled": false, "originalRoll": null, "legalValues": [], "editableIndex": null}"""
      ).value
    )
  }

  it should "be on with nothing to pick outside the picker" in {
    at(
      Serialize.game(GameState.initial(Rules(wildcard = true))),
      "houseRules",
      "wildcard",
    ).focus shouldBe Some(
      parse(
        """{"enabled": true, "originalRoll": null, "legalValues": [], "editableIndex": null}"""
      ).value
    )
  }

  it should "carry the original roll, the editable die and the values that fit while the picker is open" in {
    val open = placed(GameState.initial(Rules(wildcard = true)), PlayerId.One, Cell(0, 0), 1, 1)
      .copy(
        turn = TurnState.ChoosingWildcard,
        lastRoll = Some(Roll(6, 6)),
        wildcard = Some(PendingWildcard(Some(0), Roll(6, 6))),
      )
    val wildcard = at(Serialize.game(open), "houseRules", "wildcard")
    wildcard.get[Boolean]("enabled").value shouldBe true
    wildcard.get[List[Int]]("originalRoll").value shouldBe List(6, 6)
    wildcard.get[Int]("editableIndex").value shouldBe 0
    wildcard.get[List[Int]]("legalValues").value shouldBe List(1, 2, 3, 4, 5, 6)
  }

  private def analysed(state: GameState, records: TurnRecord*): Json =
    Serialize.analysis(Analysis.turnAnalyses(state.copy(history = records.toVector)))

  private def single(row: Int, col: Int): TurnRecord =
    TurnRecord(PlayerId.One, Roll(1, 1), Some(Rectangle(Cell(row, col), 1, 1, PlayerId.One)))

  "a serialized analysis" should "list a flagged Prize turn" in {
    val state = GameState.initial(Rules(boardSize = 6, prize = true))
    val withPrize = state.copy(board =
      state.board.copy(specialCells = Set(SpecialCell(CellKind.Prize, Cell(0, 3), 0)))
    )
    val move =
      TurnRecord(PlayerId.One, Roll(1, 4), Some(Rectangle(Cell(0, 0), 1, 4, PlayerId.One)))

    analysed(withPrize, move) shouldBe parse(
      """[{"turn":1,"axis":"prize","chosen":0,"best":10,"topLeft":[0,0],"width":4,"height":1}]"""
    ).value
  }

  it should "list a denial turn in cells with its move number" in {
    val moves = Seq(single(0, 3), single(2, 4), single(2, 5), single(3, 5))

    analysed(game(6), moves*) shouldBe parse(
      """[{"turn":4,"axis":"denial","chosen":1,"best":5,"topLeft":[1,3],"width":1,"height":1}]"""
    ).value
  }

  it should "be an empty list when nothing is flagged" in {
    analysed(game(6), TurnRecord(PlayerId.One, Roll(6, 6), None)) shouldBe Json.arr()
  }

  "a serialized series" should "carry the scores and each round's breakdown" in {
    val rules = Rules(boardSize = 6, skipLimit = 2, prize = true)
    val played = placed(
      placed(GameState.initial(rules), PlayerId.One, Cell(0, 0), 5, 1),
      PlayerId.Two,
      Cell(0, 1),
      2,
      1,
    )
    val first = played.players(PlayerId.One)
    val finished = played.copy(players =
      played.players.updated(
        PlayerId.One,
        first.copy(specialCaptures = Map(CellKind.Prize -> 1)),
      )
    )

    Serialize.series(Series(3, rules).record(finished)) shouldBe parse(
      """{"length":3,"scores":{"1":15,"2":2},"gamesPlayed":1,
        |"rounds":[{"area":{"1":5,"2":2},"prizeCaptured":{"1":1,"2":0},
        |"pitfallCaptured":{"1":0,"2":0},"stealCaptured":{"1":0,"2":0},"total":{"1":15,"2":2}}],
        |"isComplete":false,"winner":1}""".stripMargin
    ).value
  }
