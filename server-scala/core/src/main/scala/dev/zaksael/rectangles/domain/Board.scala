package dev.zaksael.rectangles.domain

import scala.annotation.tailrec

/** A wall between two neighbouring cells; the order the cells are given in does not matter. */
final case class Edge private (a: Cell, b: Cell)

object Edge:
  def between(x: Cell, y: Cell): Edge =
    if Ordering[(Int, Int)].lteq((x.row, x.col), (y.row, y.col)) then new Edge(x, y)
    else new Edge(y, x)

/** A connected group of empty cells, who borders it, and whether it reaches the board edge. */
final private case class Pocket(cells: Set[Cell], owners: Set[PlayerId], touchesEdge: Boolean)

final case class Board(
    size: Int = Constants.BOARD_SIZE,
    specialCells: Set[SpecialCell] = Set.empty,
    wallEdges: Set[Edge] = Set.empty,
    obstacleCells: Set[Cell] = Set.empty,
    owners: Map[Cell, PlayerId] = Map.empty,
):
  def ownerAt(cell: Cell): Option[PlayerId] = owners.get(cell)

  def isEmpty(cell: Cell): Boolean =
    inBounds(cell) && !owners.contains(cell) && !obstacleCells.contains(cell)

  /** Empty cells sharing an edge with one of the player's cells. */
  def frontier(player: PlayerId): Set[Cell] =
    for
      cell <- owners.keySet if owners(cell) == player
      next <- cell.neighbors if isEmpty(next) && !isEdgeWalled(cell, next)
    yield next

  def isEdgeWalled(a: Cell, b: Cell): Boolean = wallEdges.contains(Edge.between(a, b))

  def inBounds(cell: Cell): Boolean =
    cell.row >= 0 && cell.col >= 0 && cell.row < size && cell.col < size

  def cellsOfKind(kind: CellKind): Set[Cell] =
    specialCells.collect { case SpecialCell(`kind`, location, _) => location }

  /** Empty cells the player could still grow into, however far away. */
  def reachableEmptyCells(player: Player): Set[Cell] =
    floodEmpty(
      if player.hasMoved then frontier(player.id)
      else if isEmpty(player.startCorner) then Set(player.startCorner)
      else Set.empty[Cell]
    )

  /** For each player, the empty cells in pockets that only that player's cells enclose. */
  def selfEnclosedCellCounts: Map[PlayerId, Int] =
    val empties =
      for
        row <- 0 until size
        col <- 0 until size
        cell = Cell(row, col)
        if isEmpty(cell)
      yield cell

    @tailrec def collect(
        remaining: Set[Cell],
        counts: Map[PlayerId, Int],
    ): Map[PlayerId, Int] =
      remaining.headOption match
        case None => counts
        case Some(start) =>
          val pocket = pocketAt(start)
          val updated = pocket.owners.toList match
            case owner :: Nil if !pocket.touchesEdge =>
              counts.updated(owner, counts.getOrElse(owner, 0) + pocket.cells.size)
            case _ => counts
          collect(remaining -- pocket.cells, updated)

    collect(empties.toSet, Map.empty)

  /** `seeds` and every empty cell connected to them without crossing a wall. */
  private def floodEmpty(seeds: Set[Cell]): Set[Cell] =
    @tailrec def grow(visited: Set[Cell], pending: List[Cell]): Set[Cell] = pending match
      case Nil => visited
      case cell :: rest =>
        val next = cell.neighbors.filter(n => !visited(n) && isEmpty(n) && !isEdgeWalled(cell, n))
        grow(visited ++ next, next.toList ::: rest)

    grow(seeds, seeds.toList)

  private def pocketAt(start: Cell): Pocket =
    val cells = floodEmpty(Set(start))
    val steps = cells.toList.flatMap(cell => cell.neighbors.filterNot(isEdgeWalled(cell, _)))
    Pocket(cells, steps.flatMap(owners.get).toSet, steps.exists(!inBounds(_)))
