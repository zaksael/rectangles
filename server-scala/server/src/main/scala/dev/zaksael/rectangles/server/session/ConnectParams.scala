package dev.zaksael.rectangles.server.session

import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.rules.Setup
import dev.zaksael.rectangles.server.protocol.Protocol

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
        case (rules, (name, turnOn)) =>
          rules.flatMap(current =>
            params.get(name) match
              case None | Some("false") => Some(current)
              case Some("true")         => Some(turnOn(current))
              case _                    => None
          )
      }
    yield rules

  /** A new game for `rules`; a coin flip from `dice` says who moves first. */
  def start(rules: Rules, dice: Dice): Play =
    val (state, next) = Setup.newGame(rules, None, dice)
    Play(state, next)
