package dev.zaksael.rectangles.server

import java.nio.file.Files
import java.nio.file.Path

import scala.annotation.tailrec

import io.circe.Json
import io.circe.Printer

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Player
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Placement
import dev.zaksael.rectangles.rules.Setup
import dev.zaksael.rectangles.rules.SplitMix64
import dev.zaksael.rectangles.server.session.BotTurns
import dev.zaksael.rectangles.server.session.Play

/**
 * Writes `frontend/src/dev/fixtures/enclosureCases.json`: boards with the self-enclosed counts the
 * engine computes for them. The web client re-implements the enclosure flood fill to hatch the
 * cells (the wire sends only counts), and `selfEnclosed.test.ts` checks that port against this
 * file; `EnclosureCasesSpec` checks each stored board still gets its stored counts. Rerun when the
 * enclosure rule changes, from `server-scala/`:
 * `sbt "server/Test/runMain dev.zaksael.rectangles.server.generateEnclosureCases [out.json]"`.
 */
object EnclosureCasesGenerator:
  val defaultOut = "../frontend/src/dev/fixtures/enclosureCases.json"

  private def cell(row: Int, col: Int): Cell = Cell(row, col)

  private def cellJson(at: Cell): Json = Json.arr(Json.fromInt(at.row), Json.fromInt(at.col))

  private def describe(name: String, board: Board): Json =
    val counts = board.selfEnclosedCellCounts
    val owners =
      for
        row <- 0 until board.size
        col <- 0 until board.size
        who <- board.ownerAt(cell(row, col))
      yield Json.arr(Json.fromInt(row), Json.fromInt(col), Json.fromInt(who.value))
    val walls = board.wallEdges.toList
      .map(edge => List(edge.a, edge.b).sortBy(c => (c.row, c.col)))
      .sortBy(pair => (pair.head.row, pair.head.col, pair.last.row, pair.last.col))
    Json.obj(
      "name"   -> Json.fromString(name),
      "size"   -> Json.fromInt(board.size),
      "owners" -> Json.arr(owners*),
      "obstacles" -> Json.arr(
        board.obstacleCells.toList.sortBy(c => (c.row, c.col)).map(cellJson)*
      ),
      "walls" -> Json.arr(walls.map(pair => Json.arr(pair.map(cellJson)*))*),
      "expected" -> Json.obj(
        "1" -> Json.fromInt(counts.getOrElse(PlayerId.One, 0)),
        "2" -> Json.fromInt(counts.getOrElse(PlayerId.Two, 0)),
      ),
    )

  final private case class Piece(who: PlayerId, row: Int, col: Int, width: Int, height: Int)

  private def built(
      name: String,
      size: Int,
      pieces: List[Piece],
      obstacles: Set[Cell] = Set.empty,
      walls: Set[Edge] = Set.empty,
  ): Json =
    val players = Map(
      PlayerId.One -> Player(PlayerId.One, "Player 1", cell(0, 0)),
      PlayerId.Two -> Player(PlayerId.Two, "Player 2", cell(size - 1, size - 1)),
    )
    val (board, _) =
      pieces.foldLeft((Board(size, wallEdges = walls, obstacleCells = obstacles), players)) {
        case ((board, players), piece) =>
          val result = Placement.place(
            board,
            players(piece.who),
            cell(piece.row, piece.col),
            piece.width,
            piece.height,
          )
          (result.board, players.updated(piece.who, result.player))
      }
    describe(name, board)

  /** Four pieces around the single cell (row, col). */
  private def ring(who: PlayerId, row: Int, col: Int): List[Piece] = List(
    Piece(who, row - 1, col - 1, 3, 1),
    Piece(who, row, col - 1, 1, 1),
    Piece(who, row, col + 1, 1, 1),
    Piece(who, row + 1, col - 1, 3, 1),
  )

  private def handBuilt: List[Json] =
    import PlayerId.{One, Two}
    List(
      built("a pocket one player closed off", 7, ring(One, 3, 3)),
      built(
        "a pocket that touches the board edge is exempt",
        7,
        List(Piece(One, 1, 2, 3, 1), Piece(One, 0, 2, 1, 1), Piece(One, 0, 4, 1, 1)),
      ),
      built(
        "an obstacle on the rim leaves the pocket enclosed",
        7,
        List(Piece(One, 2, 2, 3, 1), Piece(One, 3, 2, 1, 1), Piece(One, 4, 2, 3, 1)),
        obstacles = Set(cell(3, 4)),
      ),
      built(
        "an opponent cell across a wall does not share the pocket",
        7,
        ring(One, 3, 3).take(2) ++ ring(One, 3, 3).drop(3) :+ Piece(Two, 3, 4, 1, 1),
        walls = Set(Edge.between(cell(3, 3), cell(3, 4))),
      ),
      built(
        "a pocket bordering both players is nobody's",
        7,
        ring(One, 3, 3).take(2) ++ ring(One, 3, 3).drop(3) :+ Piece(Two, 3, 4, 1, 1),
      ),
      built("each player closes off a pocket", 9, ring(One, 2, 2) ++ ring(Two, 6, 6)),
      built(
        "a pocket of four cells",
        9,
        List(
          Piece(One, 1, 1, 4, 1),
          Piece(One, 4, 1, 4, 1),
          Piece(One, 2, 1, 1, 2),
          Piece(One, 2, 4, 1, 2),
        ),
      ),
    )

  private val allRules = Rules(
    boardSize = 19,
    wildcard = true,
    reroll = true,
    walls = true,
    obstacles = true,
    prize = true,
    pitfall = true,
    steal = true,
    selfEnclosedPenalty = true,
    comebackNudge = true,
  )

  /**
   * A seeded bot game (Greedy against Blocking), stopped before the roll once `stopAt` moves are
   * played.
   */
  private def played(seed: Long, stopAt: Option[Int]): GameState =
    val (state, dice) = Setup.newGame(allRules, Some(PlayerId.One), SplitMix64(seed))
    @tailrec def go(play: Play): GameState =
      val atStop =
        stopAt.exists(n =>
          play.state.turn == TurnState.AwaitingRoll && play.state.history.size >= n
        )
      if play.state.turn == TurnState.GameOver || atStop then play.state
      else
        val difficulty =
          if play.state.current == PlayerId.One then BotDifficulty.Greedy
          else BotDifficulty.Blocking
        BotTurns.step(play, difficulty) match
          case Some(next) => go(next)
          case None       => play.state
    go(Play(state, dice))

  private def realGames: List[Json] =
    (1L to 3L).toList.flatMap { seed =>
      List(
        describe(s"a real 19x19 game, seed $seed, after 25 moves", played(seed, Some(25)).board),
        describe(s"a real 19x19 game, seed $seed, final board", played(seed, None).board),
      )
    }

  /** One board per line, so the diff stays readable. */
  private val printer = Printer.noSpaces.copy(
    colonRight = " ",
    objectCommaRight = " ",
    arrayCommaRight = " ",
  )

  def write(out: Path): Int =
    val cases = handBuilt ++ realGames
    Files.writeString(out, cases.map(printer.print).mkString("[\n", ",\n", "\n]\n"))
    cases.size

@main def generateEnclosureCases(out: String*): Unit =
  val path    = Path.of(out.headOption.getOrElse(EnclosureCasesGenerator.defaultOut))
  val written = EnclosureCasesGenerator.write(path)
  println(s"wrote $path: $written boards")
