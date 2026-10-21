package dev.zaksael.rectangles.server

import io.circe.Json
import org.scalatest.EitherValues
import org.scalatest.OptionValues
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.TurnState
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.Turns
import dev.zaksael.rectangles.server.protocol.Serialize

class VanillaGoldenSpec extends AnyFlatSpec with Matchers with EitherValues with OptionValues:
  /** Applies one recorded client message the way the server will: roll, place, surrender. */
  private def apply(state: GameState, dice: Dice, message: Json): (GameState, Dice) =
    val cursor = message.hcursor
    cursor.get[String]("type").value match
      case "roll" =>
        Turns.rollDice(state, dice).value
      case "place" =>
        val corner = cursor.get[(Int, Int)]("topLeft").value
        val placed = Turns
          .attemptPlace(
            state,
            Cell(corner._1, corner._2),
            cursor.get[Int]("width").value,
            cursor.get[Int]("height").value,
          )
          .value
        val checked = Turns.checkGameOver(placed)
        (if checked.turn == TurnState.GameOver then checked else Turns.endTurn(checked), dice)
      case _ => (Turns.surrender(state), dice)

  "the vanilla golden game" should "serialize like the Python recording at every step before it ends" in {
    val golden = Golden.load("vanilla").value
    val rules  = Rules(boardSize = golden.connect("boardSize").toInt)
    val start =
      (GameState.initial(rules), ReplayDice(golden.draws.toList): Dice, List.empty[String])
    val (_, dice, differences) =
      golden.steps.zipWithIndex.foldLeft(start) { case ((state, dice, found), (step, index)) =>
        val (next, nextDice) = step.send.fold((state, dice))(apply(state, dice, _))
        val expected         = step.receive.head.hcursor.downField("game").focus.value
        val ended = expected.hcursor.downField("turn").get[String]("turnState").value == "gameOver"
        val stepDiff =
          if ended then Nil
          else JsonDiff.diff(expected, Serialize.game(next)).map(path => s"step $index $path")
        (next, nextDice, found ++ stepDiff)
      }
    differences shouldBe empty
    dice should matchPattern { case ReplayDice(Nil, Nil) => }
  }
