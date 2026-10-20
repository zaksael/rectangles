package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.Scene
import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.Edge
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rectangle
import dev.zaksael.rectangles.domain.SpecialCell
import dev.zaksael.rectangles.makePlayers

class PlacementSpec extends AnyFlatSpec with Matchers:
  "placing a piece" should "be refused outside the board" in {
    val board   = Board(size = 6)
    val (p1, _) = makePlayers(6)
    Placement.canPlace(board, p1, Cell(0, 0), 7, 1) shouldBe false
    Placement.canPlace(board, p1, Cell(4, 4), 3, 1) shouldBe false
    Placement.canPlace(board, p1, Cell(-1, 0), 2, 2) shouldBe false
  }

  it should "mark the covered cells as owned and record the piece" in {
    val board   = Board(size = 6)
    val (p1, _) = makePlayers(6)
    val result  = Placement.place(board, p1, Cell(1, 1), 2, 3)
    result.rectangle shouldBe Rectangle(Cell(1, 1), 2, 3, p1.id)
    result.player.pieces shouldBe Vector(result.rectangle)
    for
      row <- 1 to 3
      col <- 1 to 2
    do result.board.ownerAt(Cell(row, col)) shouldBe Some(p1.id)
    result.board.isEmpty(Cell(0, 0)) shouldBe true
  }

  it should "be refused over cells that are already taken" in {
    val scene = Scene.on(Board(size = 6)).place(PlayerId.One, Cell(0, 0), 3, 3)
    scene.canPlace(PlayerId.Two, Cell(2, 2), 2, 2) shouldBe false
  }

  it should "refuse a first piece that is not anchored at the start corner" in {
    val scene = Scene.on(Board(size = 6))
    scene.canPlace(PlayerId.One, Cell(1, 0), 2, 2) shouldBe false
    scene.canPlace(PlayerId.One, Cell(0, 1), 2, 2) shouldBe false
  }

  it should "accept a first piece at Player 1's start corner" in {
    Scene.on(Board(size = 6)).canPlace(PlayerId.One, Cell(0, 0), 3, 2) shouldBe true
  }

  it should "accept a first piece ending at Player 2's start corner" in {
    val scene = Scene.on(Board(size = 6))
    scene.canPlace(PlayerId.Two, Cell(3, 4), 2, 3) shouldBe true
    scene.canPlace(PlayerId.Two, Cell(2, 2), 2, 2) shouldBe false
  }

  it should "require later pieces to share an edge with the player's own cells" in {
    val scene = Scene.on(Board(size = 6)).place(PlayerId.One, Cell(0, 0), 2, 2)
    scene.canPlace(PlayerId.One, Cell(3, 3), 2, 2) shouldBe false
    scene.canPlace(PlayerId.One, Cell(0, 2), 2, 2) shouldBe true
    scene.canPlace(PlayerId.One, Cell(2, 0), 2, 2) shouldBe true
  }

  it should "refuse a piece that only touches the player's cells at a corner" in {
    val scene = Scene.on(Board(size = 6)).place(PlayerId.One, Cell(0, 0), 2, 2)
    scene.canPlace(PlayerId.One, Cell(2, 2), 2, 2) shouldBe false
  }

  it should "not count the opponent's cells as adjacency" in {
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(0, 0), 2, 2)
      .place(PlayerId.Two, Cell(4, 4), 2, 2)
    scene.canPlace(PlayerId.One, Cell(3, 4), 1, 1) shouldBe false

    val grown = scene.place(PlayerId.One, Cell(0, 2), 2, 2)
    grown.canPlace(PlayerId.One, Cell(2, 2), 1, 2) shouldBe true
  }

  it should "treat special cells like any other empty cell" in {
    val specialCells = Set(
      SpecialCell(CellKind.Prize, Cell(0, 5), 0),
      SpecialCell(CellKind.Prize, Cell(5, 0), 0),
    )
    val scene = Scene.on(Board(size = 6, specialCells = specialCells))
    scene.board.cellsOfKind(CellKind.Prize) shouldBe Set(Cell(0, 5), Cell(5, 0))
    scene.canPlace(PlayerId.One, Cell(0, 0), 1, 1) shouldBe true
  }

  it should "refuse a piece that straddles a wall but not the cells on either side" in {
    val wall  = Set(Edge.between(Cell(2, 2), Cell(3, 2)))
    val scene = Scene.on(Board(size = 6, wallEdges = wall)).place(PlayerId.One, Cell(2, 1), 1, 1)
    scene.canPlace(PlayerId.One, Cell(2, 2), 1, 2) shouldBe false
    scene.board.isEmpty(Cell(2, 2)) shouldBe true
    scene.board.isEmpty(Cell(3, 2)) shouldBe true
    scene.canPlace(PlayerId.One, Cell(2, 2), 1, 1) shouldBe true
  }

  it should "not count a neighbour across a wall as adjacent" in {
    val wall  = Set(Edge.between(Cell(2, 2), Cell(3, 2)))
    val scene = Scene.on(Board(size = 6, wallEdges = wall)).place(PlayerId.One, Cell(2, 2), 1, 1)
    scene.canPlace(PlayerId.One, Cell(3, 2), 1, 1) shouldBe false
    scene.canPlace(PlayerId.One, Cell(2, 3), 1, 1) shouldBe true
  }

  it should "refuse an obstacle cell and keep it out of the frontier" in {
    val scene = Scene.on(Board(size = 6, obstacleCells = Set(Cell(2, 2)))).place(
      PlayerId.One,
      Cell(2, 1),
      1,
      1,
    )
    scene.board.isEmpty(Cell(2, 2)) shouldBe false
    scene.canPlace(PlayerId.One, Cell(2, 2), 1, 1) shouldBe false
    val frontier = scene.board.frontier(PlayerId.One)
    frontier should not contain Cell(2, 2)
    frontier should not contain Cell(2, 3)
  }

  "the legal positions of a piece" should "match checking every top-left with canPlace" in {
    val scene = Scene
      .on(Board(size = 6))
      .place(PlayerId.One, Cell(0, 0), 3, 2)
      .place(PlayerId.Two, Cell(4, 4), 2, 2)
    val expected = (for
      row <- 0 to 6 - 2
      col <- 0 to 6 - 2
      if scene.canPlace(PlayerId.One, Cell(row, col), 2, 2)
    yield Cell(row, col)).toSet
    expected should not be empty
    Placement.legalTopLefts(scene.board, scene.p1, 2, 2) shouldBe expected
  }
