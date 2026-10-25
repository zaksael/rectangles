package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.Roll
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.domain.TurnRecord
import dev.zaksael.rectangles.withSpecialCells

class AnalysisSpec extends AnyFlatSpec with Matchers:
  private val six = Rules(boardSize = 6)

  private def poolOf(state: GameState, record: TurnRecord): Set[Candidate] =
    Analysis.candidatePool(record, state.board, state.players(PlayerId.One)).toSet

  "the candidate pool" should "be both orientations of the rolled pair" in {
    // P1's first move is anchored at the start corner, so each orientation has one top-left.
    val record =
      TurnRecord(PlayerId.One, Roll(1, 4), Some(Rectangle(Cell(0, 0), 1, 4, PlayerId.One)))

    poolOf(GameState.initial(six), record) shouldBe
      Set(Candidate(Cell(0, 0), 1, 4), Candidate(Cell(0, 0), 4, 1))
  }

  it should "span every wildcard value" in {
    // Doubles (2,2) wildcard-edited to 1: the fixed die stays 2, the other takes any of 1..6.
    val record = TurnRecord(
      PlayerId.One,
      Roll(2, 1),
      Some(Rectangle(Cell(0, 0), 2, 1, PlayerId.One)),
      Some(Roll(2, 2)),
    )

    poolOf(GameState.initial(six.copy(wildcard = true)), record).map(c =>
      (c.width, c.height)
    ) shouldBe
      Set((2, 1), (1, 2), (2, 2), (2, 3), (3, 2), (2, 4), (4, 2), (2, 5), (5, 2), (2, 6), (6, 2))
  }

  "the partial axes" should "count the Prize cells under a candidate" in {
    val state    = withSpecialCells(six.copy(prize = true), CellKind.Prize, Cell(0, 3))
    val (p1, p2) = (state.players(PlayerId.One), state.players(PlayerId.Two))
    val before   = state.board.reachableEmptyCells(p2).size

    def axes(candidate: Candidate) =
      Analysis.partialAxes(state.rules, state.board, p1, p2, candidate, before)

    val alongRow   = axes(Candidate(Cell(0, 0), 4, 1))
    val downColumn = axes(Candidate(Cell(0, 0), 1, 4))

    (alongRow.prizeCells, alongRow.pitfallCells, alongRow.enclosureDelta) shouldBe (1, 0, 0)
    downColumn.prizeCells shouldBe 0
  }

  "the ranking value" should "weigh Prize points and add denial at one" in {
    val axes = AxisBreakdown(
      prizeCells = 2,
      pitfallCells = 1,
      stealCells = 0,
      denialCells = 7,
      enclosureDelta = 0,
    )

    Analysis.rankingValue(axes) shouldBe 2 * 10 - 10 + 7
  }

  private def special(state: GameState, cells: (CellKind, Cell)*): GameState =
    val all = cells.zipWithIndex.map { case ((kind, cell), index) =>
      SpecialCell(kind, cell, index)
    }
    state.copy(board = state.board.copy(specialCells = all.toSet))

  /** A wall between rows 3 and 4 across the whole 6 x 6 board. */
  private def wallAcross(state: GameState): GameState =
    state.copy(board =
      state.board.copy(wallEdges = (0 until 6).map(c => Edge.between(Cell(3, c), Cell(4, c))).toSet)
    )

  private def move(
      who: PlayerId,
      roll: (Int, Int),
      topLeft: (Int, Int),
      width: Int,
      height: Int,
      original: Option[Roll] = None,
  ): TurnRecord =
    TurnRecord(
      who,
      Roll(roll._1, roll._2),
      Some(Rectangle(Cell(topLeft._1, topLeft._2), width, height, who)),
      original,
    )

  private def single(who: PlayerId, row: Int, col: Int): TurnRecord =
    move(who, (1, 1), (row, col), 1, 1)

  private def played(state: GameState, records: TurnRecord*): GameState =
    state.copy(history = records.toVector)

  private def flagged(state: GameState): Map[Int, TurnAnalysis] = Analysis.turnAnalyses(state)

  private def better(row: Int, col: Int, width: Int, height: Int): Candidate =
    Candidate(Cell(row, col), width, height)

  "the turn analyses" should "be empty for a game with no moves" in {
    flagged(GameState.initial(six)) shouldBe Map.empty
  }

  it should "never flag a skip" in {
    val skip = TurnRecord(PlayerId.One, Roll(6, 6), None)

    flagged(played(GameState.initial(six), skip)) shouldBe Map.empty
  }

  it should "flag a missed Prize capture" in {
    // The chosen 1x4 strip down column 0 misses the Prize at (0, 3); the 4x1 along row 0 takes it.
    val state = withSpecialCells(six.copy(prize = true), CellKind.Prize, Cell(0, 3))

    flagged(played(state, move(PlayerId.One, (1, 4), (0, 0), 1, 4))) shouldBe
      Map(1 -> TurnAnalysis(AnalysisAxis.Prize, 0, 10, better(0, 0, 4, 1)))
  }

  it should "flag a hit Pitfall the other orientation avoids" in {
    val state = withSpecialCells(six.copy(pitfall = true), CellKind.Pitfall, Cell(0, 3))

    flagged(played(state, move(PlayerId.One, (1, 4), (0, 0), 4, 1))) shouldBe
      Map(1 -> TurnAnalysis(AnalysisAxis.Pitfall, -10, 0, better(0, 0, 1, 4)))
  }

  it should "flag a missed Steal capture at double weight" in {
    // A Steal swings both totals, so it outranks a Prize; the points shown are the mover's own.
    val state = withSpecialCells(six.copy(steal = true), CellKind.Steal, Cell(0, 3))

    flagged(played(state, move(PlayerId.One, (1, 4), (0, 0), 1, 4))) shouldBe
      Map(1 -> TurnAnalysis(AnalysisAxis.Steal, 0, 10, better(0, 0, 4, 1)))
  }

  it should "name the axis with the larger weighted gap" in {
    // The chosen 1x4 misses two Prizes (20) and hits a Pitfall (10); the 4x1 does the opposite.
    // Points combine (-10 vs 20) but the label names the bigger contributor, the Prize.
    val state = special(
      GameState.initial(six.copy(prize = true, pitfall = true)),
      CellKind.Prize   -> Cell(0, 2),
      CellKind.Prize   -> Cell(0, 3),
      CellKind.Pitfall -> Cell(2, 0),
    )

    flagged(played(state, move(PlayerId.One, (1, 4), (0, 0), 1, 4))) shouldBe
      Map(1 -> TurnAnalysis(AnalysisAxis.Prize, -10, 20, better(0, 0, 4, 1)))
  }

  it should "ignore leftover Pitfall cells when the rule is off" in {
    val state = withSpecialCells(six, CellKind.Pitfall, Cell(0, 3))

    flagged(played(state, move(PlayerId.One, (1, 4), (0, 0), 4, 1))) shouldBe Map.empty
  }

  it should "flag a missed denial in cells" in {
    // (1, 3) is a chokepoint: taking it cuts P2 off from a 4-cell pocket without touching P2's
    // frontier. The played move at (3, 5) denies only itself.
    val state = played(
      GameState.initial(six),
      single(PlayerId.One, 0, 3),
      single(PlayerId.One, 2, 4),
      single(PlayerId.One, 2, 5),
      single(PlayerId.One, 3, 5),
    )

    flagged(state) shouldBe Map(4 -> TurnAnalysis(AnalysisAxis.Denial, 1, 5, better(1, 3, 1, 1)))
  }

  it should "flag a self-created enclosure" in {
    // A wall cuts P2 off from rows 0-3, so sealing the ring around (2, 2) earns no denial credit
    // and the enclosure penalty alone decides. Every move outside the ring ties, so the first one
    // row by row is the better candidate.
    val state = played(
      wallAcross(GameState.initial(six.copy(selfEnclosedPenalty = true))),
      single(PlayerId.Two, 5, 5),
      single(PlayerId.One, 1, 2),
      single(PlayerId.One, 3, 2),
      single(PlayerId.One, 2, 1),
      single(PlayerId.One, 2, 3),
    )

    flagged(state) shouldBe Map(5 -> TurnAnalysis(
      AnalysisAxis.Enclosure,
      -1,
      0,
      better(0, 2, 1, 1),
    ))
  }

  it should "not flag a forced move" in {
    // The closing 2x2 has exactly one legal position, so sealing a hole with it was unavoidable.
    val p2Cell  = (5, 5)
    val empties = Set((2, 2), (2, 3), (2, 4), (2, 5), (3, 4), (3, 5))
    val fill =
      for
        row <- 0 until 6
        col <- 0 until 6
        if !empties((row, col)) && (row, col) != p2Cell
      yield single(PlayerId.One, row, col)
    val history = fill :+ single(PlayerId.Two, p2Cell._1, p2Cell._2) :+
      move(PlayerId.One, (2, 2), (2, 4), 2, 2)

    flagged(played(GameState.initial(six.copy(selfEnclosedPenalty = true)), history*))
      .keySet should not contain history.size
  }

  it should "flag a suboptimal wildcard pick" in {
    // Doubles (2, 2) edited down to 1: the chosen 2x1 cannot reach the Prize at (0, 3); a 6x2 can.
    val state =
      withSpecialCells(six.copy(prize = true, wildcard = true), CellKind.Prize, Cell(0, 3))

    flagged(played(state, move(PlayerId.One, (2, 1), (0, 0), 1, 2, Some(Roll(2, 2))))) shouldBe
      Map(1 -> TurnAnalysis(AnalysisAxis.Prize, 0, 10, better(0, 0, 6, 2)))
  }

  it should "leave an optimal wildcard pick unflagged" in {
    val state =
      withSpecialCells(six.copy(prize = true, wildcard = true), CellKind.Prize, Cell(0, 3))

    flagged(played(state, move(PlayerId.One, (2, 6), (0, 0), 6, 2, Some(Roll(2, 2))))) shouldBe
      Map.empty
  }

  it should "anchor the second player at their real corner" in {
    // P2's first move belongs at (5, 5); a wrong anchor would leave the pool empty or mismatched.
    val state = played(
      GameState.initial(six),
      move(PlayerId.One, (2, 2), (0, 0), 2, 2),
      move(PlayerId.Two, (3, 3), (3, 3), 3, 3),
    )

    flagged(state).keySet should not contain 2
  }

  it should "find the same winner as an exhaustive scan when it prunes" in {
    // Enclosure + wildcard is where the ceiling prune applies; the winner must be the one a full
    // scan finds.
    val rules = six.copy(prize = true, wildcard = true, selfEnclosedPenalty = true)
    val state = played(
      wallAcross(withSpecialCells(rules, CellKind.Prize, Cell(0, 3), Cell(3, 0))),
      move(PlayerId.One, (2, 1), (0, 0), 2, 1, Some(Roll(2, 2))),
    )
    val (p1, p2) = (state.players(PlayerId.One), state.players(PlayerId.Two))
    val before   = state.board.reachableEmptyCells(p2).size
    val pool     = Analysis.candidatePool(state.history.head, state.board, p1)
    val values =
      pool.map(c =>
        c -> Analysis.rankingValue(Analysis.fullAxes(rules, state.board, p1, p2, c, before, 0))
      ).toMap

    val analysis = flagged(state).getOrElse(1, fail("turn 1 was not flagged"))

    values(analysis.better) shouldBe values.values.max
  }
