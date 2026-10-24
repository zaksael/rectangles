package dev.zaksael.rectangles.server.session

import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.Setup
import dev.zaksael.rectangles.server.protocol.Protocol

object ConnectParams:
  /** A house-rule flag: how it turns its rule on, and whether the server builds that rule yet. */
  final private case class Flag(turnOn: Rules => Rules, supported: Boolean)

  /**
   * The web client sends every house-rule flag; a rule not built yet is only allowed as "false".
   */
  private val ruleFlags: Map[String, Flag] = Map(
    "wildcardEnabled"            -> Flag(_.copy(wildcard = true), supported = false),
    "rerollEnabled"              -> Flag(_.copy(reroll = true), supported = false),
    "wallsEnabled"               -> Flag(_.copy(walls = true), supported = true),
    "obstaclesEnabled"           -> Flag(_.copy(obstacles = true), supported = true),
    "prizeEnabled"               -> Flag(_.copy(prize = true), supported = true),
    "pitfallEnabled"             -> Flag(_.copy(pitfall = true), supported = true),
    "stealEnabled"               -> Flag(_.copy(steal = true), supported = true),
    "selfEnclosedPenaltyEnabled" -> Flag(_.copy(selfEnclosedPenalty = true), supported = true),
    "comebackNudgeEnabled"       -> Flag(_.copy(comebackNudge = true), supported = false),
  )
  private val known = Set("protocolVersion", "boardSize", "skipLimit") ++ ruleFlags.keySet

  /** The rules a connect asks for, or None when any parameter is unknown or not allowed. */
  def parse(params: Map[String, String]): Option[Rules] =
    def preset(name: String, allowed: Vector[Int], default: Int): Option[Int] =
      params.get(name).fold(Some(default))(_.toIntOption.filter(allowed.contains))
    for
      _ <- Option.when(params.keySet.subsetOf(known))(())
      _ <- params.get("protocolVersion").flatMap(_.toIntOption).filter(_ == Protocol.Version)
      boardSize <- preset("boardSize", Constants.BOARD_SIZE_PRESETS, Constants.BOARD_SIZE)
      skipLimit <- preset("skipLimit", Constants.SKIP_LIMIT_PRESETS, Constants.SKIP_LIMIT)
      rules <- ruleFlags.foldLeft(Option(Rules(boardSize = boardSize, skipLimit = skipLimit))) {
        case (rules, (name, flag)) =>
          rules.flatMap(current =>
            params.get(name) match
              case None | Some("false")           => Some(current)
              case Some("true") if flag.supported => Some(flag.turnOn(current))
              case _                              => None
          )
      }
    yield rules

  /** A new game for `rules`; a coin flip from `dice` says who moves first. */
  def start(rules: Rules, dice: Dice): Play =
    val (state, next) = Setup.newGame(rules, None, dice)
    Play(state, next)
