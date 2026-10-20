package dev.zaksael.rectangles.domain

import java.nio.file.Files
import java.nio.file.Path

import io.circe.Decoder
import io.circe.parser
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

/** The boards the web client's flood-fill is checked against too (`enclosureCases.json`). */
final case class EnclosureCase(
    name: String,
    size: Int,
    owners: List[(Int, Int, Int)],
    obstacles: List[(Int, Int)],
    walls: List[((Int, Int), (Int, Int))],
    expected: Map[String, Int],
) derives Decoder

class EnclosureCasesSpec extends AnyFlatSpec with Matchers:
  private val fixture = Path.of("../frontend/src/dev/fixtures/enclosureCases.json")
  private val cases   = parser.decode[List[EnclosureCase]](Files.readString(fixture)).toOption.get

  private def cell(position: (Int, Int)): Cell = Cell(position._1, position._2)

  cases.foreach { stored =>
    s"the stored board '${stored.name}'" should "keep its stored enclosed counts" in {
      val board = Board(
        size = stored.size,
        wallEdges = stored.walls.map((a, b) => Edge.between(cell(a), cell(b))).toSet,
        obstacleCells = stored.obstacles.map(cell).toSet,
        owners =
          stored.owners.map((row, col, who) => Cell(row, col) -> PlayerId.values(who - 1)).toMap,
      )
      val counts = board.selfEnclosedCellCounts
      Map(
        "1" -> counts.getOrElse(PlayerId.One, 0),
        "2" -> counts.getOrElse(PlayerId.Two, 0),
      ) shouldBe
        stored.expected
    }
  }
