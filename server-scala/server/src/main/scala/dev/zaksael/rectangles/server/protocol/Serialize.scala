package dev.zaksael.rectangles.server.protocol

import io.circe.Json

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.ScoreBreakdown
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Scoring

object Serialize:
  private val RecentTurns = 6

  /**
   * The `game` part of a `state` message. The house-rule parts that have no rule yet are written in
   * their switched-off form; each rule fills its part in with its own task.
   */
  def game(state: GameState): Json = Json.obj(
    "board" -> Json.obj(
      "size"      -> Json.fromInt(state.board.size),
      "skipLimit" -> Json.fromInt(state.rules.skipLimit),
    ),
    "turn" -> Json.obj(
      "currentPlayerId" -> Json.fromInt(state.current.value),
      "turnState"       -> Json.fromString(turnState(state.turn)),
      "lastRoll"        -> state.lastRoll.fold(Json.Null)(roll),
      "legalPlacements" -> Json.arr(legalPlacements(state)*),
      "recentTurns"     -> Json.arr(recentTurns(state)*),
    ),
    "houseRules" -> houseRules(state),
    "players"    -> byPlayer(player(state, _)),
    "gameOver" -> Json.obj(
      "reason"   -> Json.Null,
      "playerId" -> Json.Null,
      "winner"   -> Json.Null,
      "history"  -> Json.Null,
    ),
  )

  private def turnState(turn: TurnState): String = turn match
    case TurnState.AwaitingRoll      => "awaitingRoll"
    case TurnState.ChoosingPlacement => "choosingPlacement"
    case TurnState.Skipped           => "skipped"
    case TurnState.GameOver          => "gameOver"

  private def byPlayer(value: PlayerId => Json): Json =
    Json.obj(PlayerId.values.toSeq.map(who => who.value.toString -> value(who))*)

  private def cell(at: Cell): Json = Json.arr(Json.fromInt(at.row), Json.fromInt(at.col))

  private def roll(rolled: Roll): Json =
    Json.arr(Json.fromInt(rolled.first), Json.fromInt(rolled.second))

  private def piece(rectangle: Rectangle): Json = Json.obj(
    "topLeft" -> cell(rectangle.topLeft),
    "width"   -> Json.fromInt(rectangle.width),
    "height"  -> Json.fromInt(rectangle.height),
  )

  private def breakdown(parts: ScoreBreakdown): Json = Json.obj(
    "area"      -> Json.fromInt(parts.area),
    "prize"     -> Json.fromInt(parts.prize),
    "pitfall"   -> Json.fromInt(parts.pitfall),
    "steal"     -> Json.fromInt(parts.steal),
    "enclosure" -> Json.fromInt(parts.enclosure),
  )

  /** One entry per way to hold the roll that has a legal spot: the roll as rolled, then turned. */
  private def legalPlacements(state: GameState): Seq[Json] =
    state.lastRoll.toSeq
      .flatMap(rolled => Seq(rolled, Roll(rolled.second, rolled.first)).distinct)
      .flatMap(rolled => state.legal.get(rolled).filter(_.nonEmpty).map(rolled -> _))
      .map { case (rolled, spots) =>
        Json.obj(
          "width"    -> Json.fromInt(rolled.first),
          "height"   -> Json.fromInt(rolled.second),
          "topLefts" -> Json.arr(spots.toSeq.sortBy(c => (c.row, c.col)).map(cell)*),
        )
      }

  private def houseRules(state: GameState): Json =
    def enabled(on: Boolean) = Json.obj("enabled" -> Json.fromBoolean(on))
    def special(on: Boolean, kind: CellKind) = Json.obj(
      "enabled" -> Json.fromBoolean(on),
      "cells"   -> Json.arr(),
      "points"  -> Json.fromInt(Constants.SPECIAL_CELL_KINDS(kind).points),
    )
    Json.obj(
      "wildcard" -> Json.obj(
        "enabled"       -> Json.fromBoolean(state.rules.wildcard),
        "originalRoll"  -> Json.Null,
        "legalValues"   -> Json.arr(),
        "editableIndex" -> Json.Null,
      ),
      "reroll" -> Json.obj(
        "enabled"   -> Json.fromBoolean(state.rules.reroll),
        "canReroll" -> Json.False,
      ),
      "comebackNudge" -> enabled(state.rules.comebackNudge),
      "walls" -> Json.obj("enabled" -> Json.fromBoolean(state.rules.walls), "edges" -> Json.arr()),
      "obstacles" -> Json.obj(
        "enabled" -> Json.fromBoolean(state.rules.obstacles),
        "cells"   -> Json.arr(),
      ),
      "prize"               -> special(state.rules.prize, CellKind.Prize),
      "pitfall"             -> special(state.rules.pitfall, CellKind.Pitfall),
      "steal"               -> special(state.rules.steal, CellKind.Steal),
      "selfEnclosedPenalty" -> enabled(state.rules.selfEnclosedPenalty),
    )

  /** The last few moves, oldest first; `points` is the mover's own score change on that move. */
  private def recentTurns(state: GameState): Seq[Json] =
    val steps = Scoring.breakdownHistory(state)
    state.history
      .zip(steps)
      .zipWithIndex
      .map { case ((record, step), index) =>
        val before = if index == 0 then 0 else steps(index - 1)(record.playerId).total
        Json.obj(
          "turn"                 -> Json.fromInt(index + 1),
          "playerId"             -> Json.fromInt(record.playerId.value),
          "roll"                 -> roll(record.roll),
          "placed"               -> record.placed.fold(Json.Null)(piece),
          "wildcardOriginalRoll" -> Json.Null,
          "score"                -> byPlayer(who => Json.fromInt(step(who).total)),
          "breakdown"            -> byPlayer(who => breakdown(step(who))),
          "points"               -> Json.fromInt(step(record.playerId).total - before),
        )
      }
      .takeRight(RecentTurns)

  private def player(state: GameState, who: PlayerId): Json =
    val self      = state.players(who)
    val potential = Scoring.potential(state.board, self)
    def captured(kind: CellKind) =
      Json.obj("captured" -> Json.fromInt(self.specialCaptures.getOrElse(kind, 0)))
    Json.obj(
      "name" -> Json.fromString(self.name),
      "board" -> Json.obj(
        "startCorner" -> cell(self.startCorner),
        "pieces" -> Json.arr(self.pieces.map(p =>
          piece(p).mapObject(_.add("owner", Json.fromInt(p.owner.value)))
        )*),
        "consecutiveSkips" -> Json.fromInt(self.consecutiveSkips),
      ),
      "score" -> Json.obj(
        "totalArea"  -> Json.fromInt(self.totalArea),
        "totalScore" -> Json.fromInt(Scoring.total(state, who)),
        "breakdown"  -> breakdown(Scoring.breakdown(state, who)),
        "potential" -> Json.obj(
          "area"  -> Json.fromInt(potential.area),
          "prize" -> Json.obj("points" -> Json.fromInt(potential.prizePoints)),
        ),
      ),
      "houseRules" -> Json.obj(
        "reroll" -> Json.obj("used" -> Json.fromInt(self.rerollsUsed), "limit" -> Json.fromInt(0)),
        "comebackNudge"       -> Json.obj("granted" -> Json.fromBoolean(self.comebackNudgeGranted)),
        "selfEnclosedPenalty" -> Json.obj("cells" -> Json.fromInt(0)),
        "prize"               -> captured(CellKind.Prize),
        "pitfall"             -> captured(CellKind.Pitfall),
        "steal"               -> captured(CellKind.Steal),
      ),
    )
