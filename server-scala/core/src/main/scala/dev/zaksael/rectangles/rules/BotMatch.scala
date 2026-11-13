package dev.zaksael.rectangles.rules

import scala.annotation.tailrec

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.GameOverReason
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.domain.Seats
import dev.zaksael.rectangles.domain.TurnState

/** How one bot-versus-bot game ended; the winner is None for a tie. */
final case class MatchResult(
    winner: Option[PlayerId],
    scores: Seats[Int],
    reason: GameOverReason,
    fill: Double,
)

/** A headless game with a bot in each seat, each at its own difficulty. */
object BotMatch:
  /** None when a bot has no move before the game is over, which is a bug in the bot. */
  def play(
      rules: Rules,
      difficulties: Seats[BotDifficulty],
      starter: Option[PlayerId],
      dice: Dice,
  ): Option[MatchResult] =
    val (start, afterSetup) = Setup.newGame(rules, starter, dice)
    finish(start, difficulties, afterSetup).flatMap(result)

  @tailrec private def finish(
      state: GameState,
      difficulties: Seats[BotDifficulty],
      dice: Dice,
  ): Option[GameState] =
    if state.turn == TurnState.GameOver then Some(state)
    else
      step(state, difficulties(state.current), dice) match
        case None                => None
        case Some((next, after)) => finish(next, difficulties, after)

  /**
   * One atomic action for the player to move; None when the game is over or the bot's pick is
   * refused.
   */
  def step(
      state: GameState,
      difficulty: BotDifficulty,
      dice: Dice,
  ): Option[(GameState, Dice)] =
    if Bot.shouldReroll(state, difficulty) then Turns.reroll(state, dice).toOption
    else
      state.turn match
        case TurnState.AwaitingRoll => Turns.rollDice(state, dice).toOption
        case TurnState.ChoosingWildcard =>
          Bot.chooseWildcardValue(state, difficulty, dice).flatMap((value, next) =>
            Turns.chooseWildcard(state, value).toOption.map((_, next))
          )
        case TurnState.ChoosingPlacement =>
          Bot.choosePlacement(state, difficulty, dice).flatMap((pick, next) =>
            Turns
              .attemptPlace(state, pick.topLeft, pick.width, pick.height)
              .toOption
              .map(placed => (Turns.advance(placed), next))
          )
        case TurnState.Skipped =>
          Turns.confirmSkip(state).toOption.map(skipped => (Turns.advance(skipped), dice))
        case TurnState.GameOver => None

  private def result(end: GameState): Option[MatchResult] =
    end.gameOver.map { reason =>
      val scores = Scoring.breakdowns(end).map(_.total)
      val owned  = end.players.values.map(_.totalArea).sum
      MatchResult(
        Scoring.leader(scores.one, scores.two),
        scores,
        reason,
        owned.toDouble / (end.rules.boardSize * end.rules.boardSize),
      )
    }
