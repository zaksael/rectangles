BOARD_SIZE = 19

DICE_MIN = 1
DICE_MAX = 6

# A player who is skipped this many turns in a row ends the game.
SKIP_LIMIT = 5

# Shared by Flag Conquest and Walls: neither will place a special cell
# within this Chebyshev distance of either player's start corner, keeping
# both features clear of the opening moves.
START_CORNER_EXCLUSION_RADIUS = 5

# Minimum Chebyshev distance kept between two special cells belonging to the
# SAME house-rule feature (e.g. one Flag Conquest pair vs. the next, or one
# Wall pair vs. the next) - keeps them visually spread across the board
# instead of clustering together. Does not apply across different features
# (a flag can still land right next to a wall or an obstacle).
MIN_SPECIAL_CELL_DISTANCE = 3

# Whether flag cells are seeded on the board (see Game.reset()); capturing one
# awards FLAG_BONUS_POINTS on top of area. FLAG_CELL_PAIRS mirrored
# single-cell pairs are placed each game (each pair: a random cell outside
# START_CORNER_EXCLUSION_RADIUS plus its 180-degree rotation mirror), same
# shape as Obstacles - no fixed/center flag, so neither player is favored.
FLAG_CONQUEST_ENABLED = False
FLAG_BONUS_POINTS = 10
FLAG_CELL_PAIRS = 2

# Whether wall lines are seeded on the board (see Game.reset()). A wall is a
# barrier between cells, not a cell itself - no cell is ever sacrificed, a
# piece just can't be placed across the line. WALL_LINE_PAIRS pairs are
# placed each game, each pair's orientation (horizontal/vertical) and
# position randomized and kept outside START_CORNER_EXCLUSION_RADIUS of
# either player's start corner; every pair's second segment is its first's
# 180-degree rotation mirror, so the obstacle is always symmetric for either
# player, same reasoning as flag conquest's centered flag.
WALLS_ENABLED = False
WALL_LINE_LENGTH = 5
WALL_LINE_PAIRS = 2

# Whether obstacle cells are seeded on the board (see Game.reset()). Unlike
# Walls (which block adjacency but leave the cell itself free), an obstacle
# cell is simply never placeable - seeded into Board._grid with the
# OBSTACLE_OWNER sentinel at construction time. OBSTACLE_CELL_PAIRS mirrored
# pairs are placed each game, randomized and kept outside
# START_CORNER_EXCLUSION_RADIUS of either start corner and clear of flag
# cells/wall cells, same placement reasoning as Flag Conquest/Walls.
OBSTACLES_ENABLED = False
OBSTACLE_CELL_PAIRS = 2
OBSTACLE_OWNER = -1

# Whether a roll can become a "wildcard roll": one of the two just-rolled
# numbers (chosen at random) becomes freely editable by the player before the
# turn proceeds - see Game.roll_dice()/choose_wildcard_value(). Triggered
# whenever the roll comes up doubles (both dice matching).
WILDCARD_ENABLED = False

# Whether empty cells fully enclosed by one player's own territory dock that
# player points (see Board.self_enclosed_cell_counts()/Game.total_score()) -
# a live, dynamic penalty for leaving unfilled holes, not a one-time or
# permanent effect: it's recomputed fresh from the current board every time,
# same as total_area itself, and drops the moment the hole is broken open.
SELF_ENCLOSED_PENALTY_ENABLED = False
SELF_ENCLOSED_PENALTY_PER_CELL = 1

# Whether a player may discard their current roll and roll fresh instead of
# accepting it - see Game.reroll()/Game.can_reroll(). Capped at REROLL_LIMIT
# uses per player per game (not per turn, not per series round).
REROLL_ENABLED = False
REROLL_LIMIT = 2

# Selectable options on the pre-game settings screen. Defaults above stay
# valid members of both. Kept odd by convention; nothing currently requires it.
BOARD_SIZE_PRESETS = (19, 23, 27)
SKIP_LIMIT_PRESETS = (3, 5)
SERIES_LENGTH_PRESETS = (3, 5)

# Tournament: single-elimination bracket size, restricted to powers of two so
# every round (including round 1) is a clean pairing - no byes/seeding logic
# needed anywhere.
TOURNAMENT_SIZE_PRESETS = (4, 8)

# Chosen up front on the Game Mode select screen, before the settings screen
# (which then only shows what the chosen mode needs).
GAME_MODE_PRESETS = ("Single", "Series", "Tournament")

# Bot opponent difficulty: Basic picks a random legal placement, Greedy
# prefers capturing flags, Blocking prefers denying the opponent's frontier.
BOT_DIFFICULTY_PRESETS = ("Basic", "Greedy", "Blocking")

# Replay-screen autoplay step interval, selectable via a speed picker -
# brackets AUTO_ACTION_DELAY_MS (ui/app.py's bot-turn pacing delay, 500ms) as
# a reference point for what "one step" already feels like in this app.
REPLAY_SPEED_PRESETS = ("Slow", "Normal", "Fast")
REPLAY_SPEED_MS = {"Slow": 1200, "Normal": 600, "Fast": 250}

PLAYER_1 = 1
PLAYER_2 = 2

# RGB colors, keyed by player id.
PLAYER_COLORS = {
    PLAYER_1: (70, 130, 220),
    PLAYER_2: (220, 120, 60),
}
PLAYER_BORDER_COLORS = {
    PLAYER_1: (35, 75, 140),
    PLAYER_2: (150, 70, 25),
}
PLAYER_NAMES = {
    PLAYER_1: "Player 1",
    PLAYER_2: "Player 2",
}
