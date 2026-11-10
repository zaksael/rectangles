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

  /** One atomic action for the player to move, as the server takes it for the bot. */
  private def step(
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
              .map(placed => (advance(placed), next))
          )
        case TurnState.Skipped =>
          Turns.confirmSkip(state).toOption.map(skipped => (advance(skipped), dice))
        case TurnState.GameOver => None

  /** After a placement or a skip: end the game if it is over, else pass the turn. */
  private def advance(state: GameState): GameState =
    val checked = Turns.checkGameOver(state)
    if checked.turn == TurnState.GameOver then checked else Turns.endTurn(checked)

  private def result(end: GameState): Option[MatchResult] =
    end.gameOver.map { reason =>
      val scores = Seats(Scoring.total(end, PlayerId.One), Scoring.total(end, PlayerId.Two))
      val winner =
        if scores.one == scores.two then None
        else Some(if scores.one > scores.two then PlayerId.One else PlayerId.Two)
      val owned = PlayerId.values.map(who => Scoring.breakdown(end, who).area).sum
      MatchResult(
        winner,
        scores,
        reason,
        owned.toDouble / (end.rules.boardSize * end.rules.boardSize),
      )
    }
