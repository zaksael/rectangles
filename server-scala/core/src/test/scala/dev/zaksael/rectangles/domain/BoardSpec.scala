package dev.zaksael.rectangles.domain

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.Scene

class BoardSpec extends AnyFlatSpec with Matchers:
  "a frontier" should "be empty before the player has placed anything" in {
    Scene.on(Board(size = 6)).board.frontier(PlayerId.One) shouldBe Set.empty
  }

  it should "list the empty cells beside the player's piece" in {
    val scene = Scene.on(Board(size = 6)).place(PlayerId.One, Cell(0, 0), 3, 3)
    scene.board.frontier(PlayerId.One) shouldBe
      Set(Cell(0, 3), Cell(1, 3), Cell(2, 3), Cell(3, 0), Cell(3, 1), Cell(3, 2))
  }

  it should "leave out cells owned by either player" in {
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(0, 0), 2, 2)
      .place(PlayerId.Two, Cell(0, 2), 2, 2)
    val frontier = scene.board.frontier(PlayerId.One)
    frontier should not contain Cell(0, 2)
    frontier should not contain Cell(0, 0)
    frontier should contain(Cell(2, 0))
  }

  "a board" should "start with no special cells" in {
    val board = Board(size = 6)
    board.specialCells shouldBe Set.empty
    board.cellsOfKind(CellKind.Prize) shouldBe Set.empty
  }

  it should "start with no wall edges" in {
    Board(size = 6).wallEdges shouldBe Set.empty
  }

  it should "leave out a neighbour across a wall" in {
    val wall     = Set(Edge.between(Cell(2, 2), Cell(3, 2)))
    val scene    = Scene.on(Board(size = 6, wallEdges = wall)).place(PlayerId.One, Cell(2, 2), 1, 1)
    val frontier = scene.board.frontier(PlayerId.One)
    frontier should not contain Cell(3, 2)
    frontier should contain(Cell(2, 3))
  }

  it should "start with no obstacle cells" in {
    Board(size = 6).obstacleCells shouldBe Set.empty
  }

  "reachable cells" should "cover the whole empty board before the first piece" in {
    val scene     = Scene.on(Board(size = 6))
    val reachable = scene.board.reachableEmptyCells(scene.p1)
    reachable.size shouldBe 36
    reachable should contain(Cell(0, 0))
    reachable should contain(Cell(5, 5))
  }

  it should "reach beyond the one-hop frontier" in {
    val scene     = Scene.on(Board(size = 6)).place(PlayerId.One, Cell(0, 0), 2, 2)
    val reachable = scene.board.reachableEmptyCells(scene.p1)
    (reachable -- scene.board.frontier(PlayerId.One)) should not be empty
    reachable should contain(Cell(5, 5))
  }

  it should "stop at the opponent's territory" in {
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(0, 0), 1, 1)
      .place(PlayerId.Two, Cell(0, 3), 1, 6)
    val reachable = scene.board.reachableEmptyCells(scene.p1)
    reachable should not contain Cell(0, 3)
    reachable should contain(Cell(0, 2))
    for
      row <- 0 until 6
      col <- 4 until 6
    do reachable should not contain Cell(row, col)
  }

  it should "not cross a wall that spans the board" in {
    val wall  = (0 until 6).map(col => Edge.between(Cell(2, col), Cell(3, col))).toSet
    val scene = Scene.on(Board(size = 6, wallEdges = wall)).place(PlayerId.One, Cell(2, 2), 1, 1)
    val reachable = scene.board.reachableEmptyCells(scene.p1)
    reachable should contain(Cell(2, 3))
    for
      row <- 3 until 6
      col <- 0 until 6
    do reachable should not contain Cell(row, col)
  }

  it should "leave out obstacle cells" in {
    val scene = Scene.on(Board(size = 6, obstacleCells = Set(Cell(0, 1))))
    scene.board.reachableEmptyCells(scene.p1) should not contain Cell(0, 1)
  }

  it should "lose a whole pocket when its only connector is taken" in {
    // (1, 3) is the sole empty connector into the pocket {(0,4), (0,5), (1,4), (1,5)}, which
    // Player 1's cells already wall in on its other sides.
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(0, 3), 1, 1)
      .place(PlayerId.One, Cell(2, 4), 1, 1)
      .place(PlayerId.One, Cell(2, 5), 1, 1)
    val before = scene.board.reachableEmptyCells(scene.p2).size

    def denied(cell: Cell): Int =
      before - scene.place(PlayerId.One, cell, 1, 1).board.reachableEmptyCells(scene.p2).size

    denied(Cell(1, 3)) shouldBe 5
    denied(Cell(3, 5)) shouldBe 1
  }

  "self-enclosed cells" should "be credited for a hole bordered by one player only" in {
    // Player 2's piece gives the outer empty region a second owner, so it is not counted too.
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(1, 2), 1, 1)
      .place(PlayerId.One, Cell(3, 2), 1, 1)
      .place(PlayerId.One, Cell(2, 1), 1, 1)
      .place(PlayerId.One, Cell(2, 3), 1, 1)
      .place(PlayerId.Two, Cell(5, 5), 1, 1)
    scene.board.selfEnclosedCellCounts shouldBe Map(PlayerId.One -> 1)
  }

  it should "ignore a region bordered by both players" in {
    val scene = Scene
      .on(Board(size = 4))
      .place(PlayerId.One, Cell(0, 0), 1, 1)
      .place(PlayerId.Two, Cell(3, 3), 1, 1)
    scene.board.selfEnclosedCellCounts shouldBe Map.empty
  }

  it should "exclude a region that touches the board edge" in {
    // (0, 2) borders only Player 1's cells, but its fourth side is the board edge, which did part
    // of the enclosing for free.
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(1, 2), 1, 1)
      .place(PlayerId.One, Cell(0, 1), 1, 1)
      .place(PlayerId.One, Cell(0, 3), 1, 1)
      .place(PlayerId.Two, Cell(5, 5), 1, 1)
    scene.board.selfEnclosedCellCounts shouldBe Map.empty
  }

  it should "treat obstacle cells as neutral boundaries" in {
    val scene = Scene
      .on(Board(size = 6, obstacleCells = Set(Cell(2, 3))))
      .place(PlayerId.One, Cell(1, 2), 1, 1)
      .place(PlayerId.One, Cell(3, 2), 1, 1)
      .place(PlayerId.One, Cell(2, 1), 1, 1)
      .place(PlayerId.Two, Cell(5, 5), 1, 1)
    scene.board.selfEnclosedCellCounts shouldBe Map(PlayerId.One -> 1)
  }
