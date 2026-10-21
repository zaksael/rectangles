package dev.zaksael.rectangles.domain

enum TurnState:
  case AwaitingRoll, ChoosingPlacement, Skipped, GameOver

/** Why a game ended; the player is the one the reason is about. */
enum GameOverReason:
  case BoardFull
  case SkipLimit(who: PlayerId)
  case PlayerBlocked(who: PlayerId)
  case Surrendered(who: PlayerId)

final case class GameState(
    rules: Rules,
    board: Board,
    players: Map[PlayerId, Player],
    current: PlayerId,
    turn: TurnState,
    lastRoll: Option[Roll],
    legal: Map[Roll, Set[Cell]],
    history: Vector[TurnRecord],
    gameOver: Option[GameOverReason] = None,
)

object GameState:
  def initial(rules: Rules, starter: PlayerId = PlayerId.One): GameState =
    val last = rules.boardSize - 1
    GameState(
      rules,
      Board(size = rules.boardSize),
      Map(
        PlayerId.One -> Player(PlayerId.One, Constants.PLAYER_NAMES(PlayerId.One), Cell(0, 0)),
        PlayerId.Two -> Player(PlayerId.Two, Constants.PLAYER_NAMES(PlayerId.Two), Cell(last, last)),
      ),
      starter,
      TurnState.AwaitingRoll,
      None,
      Map.empty,
      Vector.empty,
    )
