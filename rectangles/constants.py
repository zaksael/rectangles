BOARD_SIZE = 12

DICE_MIN = 1
DICE_MAX = 6

# A player who is skipped this many turns in a row ends the game.
SKIP_LIMIT = 3

# Whether rolling doubles grants the same player another turn.
DOUBLES_ENABLED = False

# Selectable options on the pre-game settings screen. Defaults above stay
# valid members of both.
BOARD_SIZE_PRESETS = (8, 10, 12, 16)
SKIP_LIMIT_PRESETS = (2, 3, 5)
SERIES_LENGTH_PRESETS = (3, 5)

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
