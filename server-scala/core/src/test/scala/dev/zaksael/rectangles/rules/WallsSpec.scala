package dev.zaksael.rectangles.rules

import scala.annotation.tailrec

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.ScriptedDice
import dev.zaksael.rectangles.chebyshev
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules

class WallsSpec extends AnyFlatSpec with Matchers:
  /** Wall cells grouped into contiguous segments, so a segment's own adjacency is not counted. */
  private def segments(edges: Set[Edge]): List[Set[Cell]] =
    @tailrec def grow(group: Set[Cell], rest: Set[Cell]): (Set[Cell], Set[Cell]) =
      val touching = rest.filter(cell => group.exists(chebyshev(_, cell) <= 1))
      if touching.isEmpty then (group, rest) else grow(group ++ touching, rest -- touching)
    @tailrec def split(rest: Set[Cell], found: List[Set[Cell]]): List[Set[Cell]] =
      rest.headOption match
        case None => found
        case Some(seed) =>
          val (group, left) = grow(Set(seed), rest - seed)
          split(left, group :: found)
    split(edges.flatMap(edge => Set(edge.a, edge.b)), Nil)

  "a game with walls off" should "have no wall edges" in {
    Setup.newGame(
      Rules(boardSize = 11),
      Some(PlayerId.One),
      SplitMix64(0L),
    )._1.board.wallEdges shouldBe empty
  }

  "wall segments" should "stay the minimum special cell distance apart" in {
    for seed <- 0 until 30 do
      val (state, _) =
        Setup.newGame(Rules(walls = true), Some(PlayerId.One), SplitMix64(seed.toLong))
      state.board.wallEdges should not be empty
      val groups = segments(state.board.wallEdges)
      for
        (first, i) <- groups.zipWithIndex
        second     <- groups.drop(i + 1)
        a          <- first
        b          <- second
      do chebyshev(a, b) should be >= Constants.MIN_SPECIAL_CELL_DISTANCE
  }

  it should "be symmetric, bounded and clear of the corners and prize cells on odd boards" in {
    for
      size  <- List(11, 19)
      prize <- List(false, true)
    do
      val board = Setup
        .newGame(
          Rules(boardSize = size, walls = true, prize = prize),
          Some(PlayerId.One),
          ScriptedDice(List.fill(20)(0)),
        )
        ._1
        .board
      board.wallEdges should not be empty
      board.wallEdges.size should be <= 2 * Constants.WALL_LINE_PAIRS * Constants.WALL_LINE_LENGTH
      board.wallEdges.map(edge =>
        Edge.between(Generation.mirrorCell(edge.a, size), Generation.mirrorCell(edge.b, size))
      ) shouldBe board.wallEdges
      val cells = Generation.wallCells(board.wallEdges)
      cells.foreach(Generation.nearStartCorner(_, size) shouldBe false)
      cells.intersect(board.cellsOfKind(CellKind.Prize)) shouldBe empty
  }
