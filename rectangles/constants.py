BOARD_SIZE = 11

DICE_MIN = 1
DICE_MAX = 6

# A player who is skipped this many turns in a row ends the game.
SKIP_LIMIT = 3

# Whether rolling doubles grants the same player another turn.
DOUBLES_ENABLED = False

# Whether flag cells are seeded on the board (see Game.reset()); capturing one
# awards FLAG_BONUS_POINTS on top of area.
FLAG_CONQUEST_ENABLED = False
FLAG_BONUS_POINTS = 10

# Whether two wall lines are seeded on the board (see Game.reset()). A wall
# is a barrier between cells, not a cell itself - no cell is ever sacrificed,
# a piece just can't be placed across the line. One wall sits near Player 1's
# corner (upper-left of center), the other is its 180-degree rotation mirror
# near Player 2's corner (lower-right of center) - so it's symmetric for
# either player, same reasoning as flag conquest's centered flag.
WALLS_ENABLED = False
WALL_LINE_OFFSET = 2
WALL_LINE_LENGTH = 3

# Selectable options on the pre-game settings screen. Defaults above stay
# valid members of both. Board sizes are odd so flag conquest's center cell
# (size // 2) is always a single unambiguous cell.
BOARD_SIZE_PRESETS = (11, 15, 19)
SKIP_LIMIT_PRESETS = (2, 3, 5)
SERIES_LENGTH_PRESETS = (3, 5)
FLAG_BONUS_POINTS_PRESETS = (5, 10, 20)

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
