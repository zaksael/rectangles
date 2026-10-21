package dev.zaksael.rectangles

import dev.zaksael.rectangles.domain.Board
import dev.zaksael.rectangles.domain.Cell
import dev.zaksael.rectangles.domain.GameState
import dev.zaksael.rectangles.domain.Player
import dev.zaksael.rectangles.domain.PlayerId
import dev.zaksael.rectangles.rules.Placement

/** The two players of a `size` x `size` board, each starting in their own corner. */
def makePlayers(size: Int): (Player, Player) =
  (
    Player(PlayerId.One, "Player 1", Cell(0, 0)),
    Player(PlayerId.Two, "Player 2", Cell(size - 1, size - 1)),
  )

/** A board with its two players, for tests that place several pieces in a row. */
final case class Scene(board: Board, p1: Player, p2: Player):
  def player(who: PlayerId): Player = if who == PlayerId.One then p1 else p2

  def place(who: PlayerId, topLeft: Cell, width: Int, height: Int): Scene =
    val result = Placement.place(board, player(who), topLeft, width, height)
    if who == PlayerId.One then copy(board = result.board, p1 = result.player)
    else copy(board = result.board, p2 = result.player)

  def canPlace(who: PlayerId, topLeft: Cell, width: Int, height: Int): Boolean =
    Placement.canPlace(board, player(who), topLeft, width, height)

object Scene:
  def on(board: Board): Scene =
    val (p1, p2) = makePlayers(board.size)
    Scene(board, p1, p2)

/** The state with a piece put on the board for `who`, without rolling or checking legality. */
def placed(state: GameState, who: PlayerId, topLeft: Cell, width: Int, height: Int): GameState =
  val result = Placement.place(state.board, state.players(who), topLeft, width, height)
  state.copy(board = result.board, players = state.players.updated(who, result.player))
