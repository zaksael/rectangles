BOARD_SIZE = 19

DICE_MIN = 1
DICE_MAX = 6

# A player who is skipped this many turns in a row ends the game.
SKIP_LIMIT = 3

# Shared by Flag Conquest and Walls: neither will place a special cell
# within this Chebyshev distance of either player's start corner, keeping
# both features clear of the opening moves.
START_CORNER_EXCLUSION_RADIUS = 5

# Whether flag cells are seeded on the board (see Game.reset()); capturing one
# awards FLAG_BONUS_POINTS on top of area. The center flag is always seeded;
# the other two are a random cell (outside START_CORNER_EXCLUSION_RADIUS) plus
# its 180-degree rotation mirror, so neither player is favored.
FLAG_CONQUEST_ENABLED = False
FLAG_BONUS_POINTS = 10

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

# Whether a roll can become a "wildcard roll": one of the two just-rolled
# numbers (chosen at random) becomes freely editable by the player before the
# turn proceeds - see Game.roll_dice()/choose_wildcard_value(). Triggered by
# either a 1-in-6 random chance (WILDCARD_TRIGGER_VALUE) or doubles (both
# dice matching).
WILDCARD_ENABLED = False
WILDCARD_TRIGGER_VALUE = 1  # rng.randint(DICE_MIN, DICE_MAX) == this triggers it (1-in-6)

# Selectable options on the pre-game settings screen. Defaults above stay
# valid members of both. Board sizes are odd so flag conquest's center cell
# (size // 2) is always a single unambiguous cell.
BOARD_SIZE_PRESETS = (19, 23, 27)
SKIP_LIMIT_PRESETS = (2, 3, 5)
SERIES_LENGTH_PRESETS = (3, 5)
FLAG_BONUS_POINTS_PRESETS = (5, 10, 20)

# Bot opponent difficulty: Basic picks a random legal placement, Greedy
# prefers capturing flags, Blocking prefers denying the opponent's frontier.
BOT_DIFFICULTY_PRESETS = ("Basic", "Greedy", "Blocking")

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
