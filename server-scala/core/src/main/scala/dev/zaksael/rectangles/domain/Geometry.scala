package dev.zaksael.rectangles.domain

final case class Cell(row: Int, col: Int):
  /** The four cells sharing an edge, on or off the board. */
  def neighbors: Vector[Cell] =
    Vector(Cell(row - 1, col), Cell(row + 1, col), Cell(row, col - 1), Cell(row, col + 1))

final case class Rectangle(topLeft: Cell, width: Int, height: Int, owner: PlayerId):
  def area: Int = width * height

  def bottomRight: Cell = Cell(topLeft.row + height - 1, topLeft.col + width - 1)

  def cells: Iterator[Cell] =
    for
      row <- Iterator.range(topLeft.row, topLeft.row + height)
      col <- Iterator.range(topLeft.col, topLeft.col + width)
    yield Cell(row, col)
