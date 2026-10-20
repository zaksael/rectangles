package dev.zaksael.rectangles.rules

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.Player
import dev.zaksael.rectangles.domain.Rectangle

/** The board and player after a placement, and the piece that was placed. */
final case class PlacementResult(board: Board, player: Player, rectangle: Rectangle)

object Placement:
  def canPlace(
      board: Board,
      player: Player,
      topLeft: Cell,
      width: Int,
      height: Int,
  ): Boolean =
    val rectangle = Rectangle(topLeft, width, height, player.id)
    val anchored =
      rectangle.topLeft == player.startCorner || rectangle.bottomRight == player.startCorner
    val touchesOwn = rectangle.cells.exists(cell =>
      cell.neighbors.exists(next =>
        board.ownerAt(next).contains(player.id) && !board.isEdgeWalled(cell, next)
      )
    )
    val covered       = rectangle.cells.toSet
    val straddlesWall = board.wallEdges.exists(edge => covered(edge.a) && covered(edge.b))
    covered.forall(board.isEmpty) && !straddlesWall &&
    (if player.hasMoved then touchesOwn else anchored)

  /** Places the piece without checking it is legal: call `canPlace` first. */
  def place(board: Board, player: Player, topLeft: Cell, width: Int, height: Int): PlacementResult =
    val rectangle = Rectangle(topLeft, width, height, player.id)
    PlacementResult(
      board.copy(owners = board.owners ++ rectangle.cells.map(_ -> player.id)),
      player.copy(pieces = player.pieces :+ rectangle),
      rectangle,
    )

  /** Every top-left corner where a `width` x `height` piece could legally go. */
  def legalTopLefts(board: Board, player: Player, width: Int, height: Int): Set[Cell] =
    (for
      row <- 0 to board.size - height
      col <- 0 to board.size - width
      topLeft = Cell(row, col)
      if canPlace(board, player, topLeft, width, height)
    yield topLeft).toSet
