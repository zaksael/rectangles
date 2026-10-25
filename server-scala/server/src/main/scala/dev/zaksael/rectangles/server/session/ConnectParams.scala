package dev.zaksael.rectangles.server.session

import dev.zaksael.rectangles.domain.BotDifficulty
import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.Series
import dev.zaksael.rectangles.rules.Setup
import dev.zaksael.rectangles.server.protocol.Protocol

/** What a connect asks for: the house rules, and a bot for Player Two when it has a difficulty. */
final case class Connect(
    rules: Rules,
    bot: Option[BotDifficulty],
    seriesLength: Option[Int] = None,
)

object ConnectParams:
  /** The web client sends every house-rule flag; each one turns its rule on when "true". */
  private val ruleFlags: Map[String, Rules => Rules] = Map(
    "wildcardEnabled"            -> (_.copy(wildcard = true)),
    "rerollEnabled"              -> (_.copy(reroll = true)),
    "wallsEnabled"               -> (_.copy(walls = true)),
    "obstaclesEnabled"           -> (_.copy(obstacles = true)),
    "prizeEnabled"               -> (_.copy(prize = true)),
    "pitfallEnabled"             -> (_.copy(pitfall = true)),
    "stealEnabled"               -> (_.copy(steal = true)),
    "selfEnclosedPenaltyEnabled" -> (_.copy(selfEnclosedPenalty = true)),
    "comebackNudgeEnabled"       -> (_.copy(comebackNudge = true)),
  )
  private val known =
    Set(
      "protocolVersion",
      "boardSize",
      "skipLimit",
      "botSeats",
      "botDifficulty",
      "seriesLength",
    ) ++ ruleFlags.keySet

  /** What a connect asks for, or None when any parameter is unknown or not allowed. */
  def parse(params: Map[String, String]): Option[Connect] =
    def preset(name: String, allowed: Vector[Int], default: Int): Option[Int] =
      params.get(name).fold(Some(default))(_.toIntOption.filter(allowed.contains))
    for
      _ <- Option.when(params.keySet.subsetOf(known))(())
      _ <- params.get("protocolVersion").flatMap(_.toIntOption).filter(_ == Protocol.Version)
      boardSize <- preset("boardSize", Constants.BOARD_SIZE_PRESETS, Constants.BOARD_SIZE)
      skipLimit <- preset("skipLimit", Constants.SKIP_LIMIT_PRESETS, Constants.SKIP_LIMIT)
      // The only seat a bot can take is Player Two; a difficulty alone is checked, then ignored.
      _ <- preset("botSeats", Vector(2), 2)
      seriesLength <- params.get("seriesLength").fold(Option(Option.empty[Int]))(length =>
        length.toIntOption.filter(Constants.SERIES_LENGTH_PRESETS.contains).map(Some(_))
      )
      difficulty <- params.get("botDifficulty").fold(Option(BotDifficulty.Basic))(name =>
        BotDifficulty.values.find(_.toString == name)
      )
      rules <- ruleFlags.foldLeft(Option(Rules(boardSize = boardSize, skipLimit = skipLimit))) {
        case (rules, (name, turnOn)) =>
          rules.flatMap(current =>
            params.get(name) match
              case None | Some("false") => Some(current)
              case Some("true")         => Some(turnOn(current))
              case _                    => None
          )
      }
    yield Connect(rules, Option.when(params.contains("botSeats"))(difficulty), seriesLength)

  /** A new game for `rules`; a coin flip from `dice` says who moves first. */
  def start(rules: Rules, dice: Dice): Play =
    val (state, next) = Setup.newGame(rules, None, dice)
    Play(state, next)

  /**
   * The first play of a connect: a series' first round (Player One starts, no coin flip), or a
   * single game.
   */
  def open(connect: Connect, dice: Dice): Play =
    connect.seriesLength.fold(start(connect.rules, dice)) { length =>
      val series        = Series(length, connect.rules)
      val (state, next) = series.newGame(dice)
      Play(state, next, Some(series))
    }
