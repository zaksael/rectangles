package dev.zaksael.rectangles.domain

final case class Rules(
    boardSize: Int = Constants.BOARD_SIZE,
    skipLimit: Int = Constants.SKIP_LIMIT,
    wildcard: Boolean = false,
    reroll: Boolean = false,
    walls: Boolean = false,
    obstacles: Boolean = false,
    prize: Boolean = false,
    pitfall: Boolean = false,
    steal: Boolean = false,
    selfEnclosedPenalty: Boolean = false,
    comebackNudge: Boolean = false,
)

object Constants:
  val BOARD_SIZE: Int = 19
  val DICE_MIN: Int   = 1
  val DICE_MAX: Int   = 6

  /** A player skipping this many turns in a row ends the game. */
  val SKIP_LIMIT: Int = 5

  /** Special cells and walls stay more than this Chebyshev distance from both start corners. */
  val START_CORNER_EXCLUSION_RADIUS: Int = 5

  /** Minimum Chebyshev distance between cells of one feature, and between a cell and its mirror. */
  val MIN_SPECIAL_CELL_DISTANCE: Int = 3

  val PRIZE_BONUS_POINTS: Int = 10
  val PRIZE_CELL_PAIRS: Int   = 2

  val WALL_LINE_LENGTH: Int = 5
  val WALL_LINE_PAIRS: Int  = 2

  val OBSTACLE_CELL_PAIRS: Int = 2

  val SELF_ENCLOSED_PENALTY_PER_CELL: Int = 1

  val REROLL_LIMIT: Int = 2

  val PITFALL_PENALTY_POINTS: Int = 10
  val PITFALL_CELL_PAIRS: Int     = 2

  val STEAL_POINTS: Int     = 10
  val STEAL_CELL_PAIRS: Int = 1

  val SPECIAL_CELL_KINDS: Map[CellKind, CellEffect] = Map(
    CellKind.Prize   -> CellEffect(1, 0, PRIZE_BONUS_POINTS),
    CellKind.Pitfall -> CellEffect(-1, 0, PITFALL_PENALTY_POINTS),
    CellKind.Steal   -> CellEffect(1, -1, STEAL_POINTS),
  )

  /**
   * A score gap of at least this fraction of the board's area (in whole cells, rounded up)
   * permanently grants the trailing player the nudge.
   */
  val COMEBACK_NUDGE_THRESHOLD_FRACTION: Double = 0.08
  val COMEBACK_NUDGE_EXTRA_REROLLS: Int         = 1

  /** Each setting's default is one of its presets. */
  val BOARD_SIZE_PRESETS: Vector[Int]        = Vector(19, 23, 27)
  val SKIP_LIMIT_PRESETS: Vector[Int]        = Vector(3, 5)
  val SERIES_LENGTH_PRESETS: Vector[Int]     = Vector(3, 5)
  val BOT_DIFFICULTY_PRESETS: Vector[String] = Vector("Basic", "Greedy", "Blocking")

  val PLAYER_NAMES: Map[PlayerId, String] =
    Map(PlayerId.One -> "Player 1", PlayerId.Two -> "Player 2")
