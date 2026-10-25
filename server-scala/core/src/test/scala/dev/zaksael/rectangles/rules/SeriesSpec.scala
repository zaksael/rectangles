package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.CellKind
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.placed

class SeriesSpec extends AnyFlatSpec with Matchers:
  private val one = PlayerId.One
  private val two = PlayerId.Two

  private def series(length: Int = 3): Series =
    Series(length, Rules(boardSize = 6, skipLimit = 2))

  /** A game on a board wide enough for any area below, with the areas and prize captures given. */
  private def finished(
      oneArea: Int,
      onePrizes: Int,
      twoArea: Int,
      twoPrizes: Int,
  ): GameState =
    val empty = GameState.initial(Rules(boardSize = 40))
    val withAreas = List(one -> oneArea, two -> twoArea).filter(_._2 > 0).foldLeft(empty) {
      case (state, (who, area)) => placed(state, who, Cell(0, 0), area, 1)
    }
    withAreas.copy(players = withAreas.players.view.map { (who, player) =>
      who -> player.copy(specialCaptures =
        Map(CellKind.Prize -> (if who == one then onePrizes else twoPrizes))
      )
    }.toMap)

  "recording a game" should "accumulate both players' scores" in {
    val first = series().record(finished(10, 0, 4, 0))

    first.scores shouldBe Map(one -> 10, two -> 4)
    first.gamesPlayed shouldBe 1

    val second = first.record(finished(3, 0, 12, 0))

    second.scores shouldBe Map(one -> 13, two -> 16)
    second.gamesPlayed shouldBe 2
  }

  it should "store the area and prize captures of each round" in {
    val result = series().record(finished(8, 2, 4, 0))

    result.rounds should have size 1
    val round = result.rounds.head.players
    (round(one).area, round(two).area) shouldBe (8, 4)
    (round(one).prizeCaptured, round(two).prizeCaptured) shouldBe (2, 0)
    (round(one).total, round(two).total) shouldBe (28, 4)
    result.scores shouldBe Map(one -> 28, two -> 4)
  }

  it should "store the pitfall and steal captures of each round" in {
    val game = finished(8, 0, 4, 0)
    val captured = game.copy(players =
      game.players
        .updated(
          one,
          game.players(one).copy(specialCaptures = Map(CellKind.Pitfall -> 1)),
        )
        .updated(
          two,
          game.players(two).copy(specialCaptures = Map(CellKind.Steal -> 2)),
        )
    )

    val round = series().record(captured).rounds.head.players

    (round(one).pitfallCaptured, round(two).pitfallCaptured) shouldBe (1, 0)
    (round(one).stealCaptured, round(two).stealCaptured) shouldBe (0, 2)
  }

  "a series" should "not be complete until every round is played, whatever the score gap" in {
    val afterOne = series().record(finished(30, 0, 0, 0))
    afterOne.isComplete shouldBe false
    val afterTwo = afterOne.record(finished(30, 0, 0, 0))
    afterTwo.isComplete shouldBe false
    val afterThree = afterTwo.record(finished(0, 0, 1, 0))

    afterThree.isComplete shouldBe true
    afterThree.gamesPlayed shouldBe 3
  }

  it should "let a trailing round winner still win on points" in {
    val done = series()
      .record(finished(1, 0, 0, 0))
      .record(finished(0, 0, 1, 0))
      .record(finished(2, 0, 20, 0))

    done.isComplete shouldBe true
    done.winner shouldBe Some(two)
  }

  it should "have no winner when the totals tie after every round" in {
    val done = series()
      .record(finished(5, 0, 5, 0))
      .record(finished(3, 0, 3, 0))
      .record(finished(2, 0, 2, 0))

    done.isComplete shouldBe true
    done.winner shouldBe None
  }

  "a new round" should "carry the series' rules and generate its board from them" in {
    val rules = Rules(
      boardSize = 11,
      skipLimit = 4,
      wildcard = true,
      reroll = true,
      prize = true,
      pitfall = true,
      steal = true,
      selfEnclosedPenalty = true,
      comebackNudge = true,
    )

    val (game, _) = Series(5, rules).newGame(SplitMix64(1L))

    game.rules shouldBe rules
    game.board.cellsOfKind(CellKind.Prize) should not be empty
  }

  it should "have every house rule off unless the series turns it on" in {
    val (game, _) = Series(3, Rules(boardSize = 11, skipLimit = 2)).newGame(SplitMix64(1L))

    game.rules.prize shouldBe false
    game.board.specialCells shouldBe empty
  }

  it should "alternate the starting player by round" in {
    val first  = series()
    val second = first.record(finished(1, 0, 0, 0))
    val third  = second.record(finished(1, 0, 0, 0))

    first.newGame(SplitMix64(1L))._1.current shouldBe one
    second.newGame(SplitMix64(1L))._1.current shouldBe two
    third.newGame(SplitMix64(1L))._1.current shouldBe one
  }
