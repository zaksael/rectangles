package dev.zaksael.rectangles.rules

import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.Seats

class BalanceSweepSpec extends AnyFlatSpec with Matchers:
  private val small = Rules(boardSize = 6)

  "the special rules" should "turn on prize, pitfall, steal and reroll at the given board size" in {
    BalanceSweep.specialRules(23) shouldBe
      Rules(boardSize = 23, prize = true, pitfall = true, steal = true, reroll = true)
  }

  "the rule sets" should "be default, each special rule alone, then all four" in {
    BalanceSweep.ruleSets(19) shouldBe Vector(
      "default"  -> Rules(boardSize = 19),
      "prize"    -> Rules(boardSize = 19, prize = true),
      "pitfall"  -> Rules(boardSize = 19, pitfall = true),
      "steal"    -> Rules(boardSize = 19, steal = true),
      "reroll"   -> Rules(boardSize = 19, reroll = true),
      "all four" -> BalanceSweep.specialRules(19),
    )
  }

  "a pairing sweep" should "swap the seat of its first difficulty every game" in {
    val games =
      BalanceSweep.play(small, Pairing(BotDifficulty.Basic, BotDifficulty.Blocking), 4, 1L)

    games.map(_.firstSeat) shouldBe Vector(PlayerId.One, PlayerId.Two, PlayerId.One, PlayerId.Two)
  }

  it should "cover every pairing of the three difficulties, mirrors included" in {
    BalanceSweep.pairings.toSet shouldBe (for
      first  <- BotDifficulty.values.toSet
      second <- BotDifficulty.values.toSet
    yield Pairing(first, second))
  }

  it should "report games, wins, ties, seat One wins, margin, fill and end reasons in one row" in {
    val pairing = Pairing(BotDifficulty.Basic, BotDifficulty.Blocking)
    val games = Vector(
      PairingGame(
        PlayerId.One,
        MatchResult(Some(PlayerId.One), Seats(30, 20), GameOverReason.BoardFull, 0.5),
      ),
      PairingGame(
        PlayerId.Two,
        MatchResult(Some(PlayerId.One), Seats(25, 15), GameOverReason.SkipLimit(PlayerId.Two), 0.7),
      ),
      PairingGame(PlayerId.One, MatchResult(None, Seats(18, 18), GameOverReason.BoardFull, 0.6)),
    )

    val row = BalanceSweep.report(
      Vector(pairing -> games)
    ).linesIterator.toVector.last.trim.split("\\s+").toVector

    row shouldBe Vector(
      "Basic/Blocking",
      "3",
      "1",
      "1",
      "1",
      "2",
      "10.0",
      "0.60",
      "BoardFull=2,SkipLimit=1",
    )
  }
