package dev.zaksael.rectangles.server.session

import dev.zaksael.rectangles.domain.Constants
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.domain.Rules
import dev.zaksael.rectangles.rules.Dice
import dev.zaksael.rectangles.server.protocol.Protocol

object ConnectParams:
  private val known = Set("protocolVersion", "boardSize", "skipLimit")

  /** The rules a connect asks for, or None when any parameter is unknown or not allowed. */
  def parse(params: Map[String, String]): Option[Rules] =
    def preset(name: String, allowed: Vector[Int], default: Int): Option[Int] =
      params.get(name).fold(Some(default))(_.toIntOption.filter(allowed.contains))
    for
      _ <- Option.when(params.keySet.subsetOf(known))(())
      _ <- params.get("protocolVersion").flatMap(_.toIntOption).filter(_ == Protocol.Version)
      boardSize <- preset("boardSize", Constants.BOARD_SIZE_PRESETS, Constants.BOARD_SIZE)
      skipLimit <- preset("skipLimit", Constants.SKIP_LIMIT_PRESETS, Constants.SKIP_LIMIT)
    yield Rules(boardSize = boardSize, skipLimit = skipLimit)

  /** A new game for `rules`; a coin flip from `dice` says who moves first. */
  def start(rules: Rules, dice: Dice): Play =
    val (starter, next) = dice.choose(PlayerId.values.toSeq)
    Play(GameState.initial(rules, starter), next)
