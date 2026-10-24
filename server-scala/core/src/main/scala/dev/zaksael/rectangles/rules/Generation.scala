package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.Rules

/** Random placement of the board's walls and special cells, mirrored for the two players. */
object Generation:
  def mirrorCell(cell: Cell, size: Int): Cell = Cell(size - 1 - cell.row, size - 1 - cell.col)

  private def chebyshev(a: Cell, b: Cell): Int =
    math.max(math.abs(a.row - b.row), math.abs(a.col - b.col))

  def nearStartCorner(cell: Cell, size: Int): Boolean =
    Vector(Cell(0, 0), Cell(size - 1, size - 1)).exists(corner =>
      chebyshev(cell, corner) <= Constants.START_CORNER_EXCLUSION_RADIUS
    )

  def nearAny(cell: Cell, others: Set[Cell]): Boolean =
    others.exists(chebyshev(cell, _) < Constants.MIN_SPECIAL_CELL_DISTANCE)

  private def edgeCells(edges: Seq[Edge]): Set[Cell] =
    edges.flatMap(edge => Set(edge.a, edge.b)).toSet

  /** The wall segments and their mirror images, avoiding `occupied` cells. */
  def wallEdges(rules: Rules, occupied: Set[Cell], dice: Dice): (Set[Edge], Dice) =
    val size = rules.boardSize
    def segment(horizontal: Boolean, fixed: Int, start: Int): Seq[Edge] =
      (start until start + Constants.WALL_LINE_LENGTH).map { i =>
        if horizontal then Edge.between(Cell(fixed, i), Cell(fixed + 1, i))
        else Edge.between(Cell(i, fixed), Cell(i, fixed + 1))
      }
    val start = (Set.empty[Cell], occupied, Set.empty[Edge], dice)
    val (_, _, result, after) = (0 until Constants.WALL_LINE_PAIRS).foldLeft(start) {
      case ((ownPlaced, taken, edges, current), _) =>
        val (orientation, next) = current.between(0, 1)
        val candidates =
          for
            fixed <- 0 until size - 1
            from  <- 0 to size - Constants.WALL_LINE_LENGTH
            line     = segment(orientation == 0, fixed, from)
            cells    = edgeCells(line)
            mirrored = cells.map(mirrorCell(_, size))
            if !cells.exists(nearAny(_, mirrored)) &&
              !cells.exists(nearStartCorner(_, size)) && cells.intersect(taken).isEmpty &&
              !cells.exists(nearAny(_, ownPlaced))
          yield line
        if candidates.isEmpty then (ownPlaced, taken, edges, next)
        else
          val (index, last) = next.between(0, candidates.size - 1)
          val line          = candidates(index)
          val mirroredLine =
            line.map(edge => Edge.between(mirrorCell(edge.a, size), mirrorCell(edge.b, size)))
          val placed = edgeCells(line ++ mirroredLine)
          (ownPlaced ++ placed, taken ++ placed, edges ++ line ++ mirroredLine, last)
    }
    (result, after)
