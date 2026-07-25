from rectangles.constants import PLAYER_2
from rectangles.game import Game
from rectangles.ui.input import compute_top_left


def test_compute_top_left_p1_uses_cell_directly():
    game = Game(board_size=6)
    assert compute_top_left(game, w=2, h=2, cell=(2, 3)) == (2, 3)


def test_compute_top_left_p1_clamps_upper_bound():
    game = Game(board_size=6)
    # A 2x2 piece anchored at (5, 5) would overrun the board; clamp to fit.
    assert compute_top_left(game, w=2, h=2, cell=(5, 5)) == (4, 4)


def test_compute_top_left_p2_uses_cell_as_bottom_right():
    game = Game(board_size=6)
    game.current_player_id = PLAYER_2
    # A 2x2 piece with bottom-right at (5, 5) has top-left at (4, 4).
    assert compute_top_left(game, w=2, h=2, cell=(5, 5)) == (4, 4)


def test_compute_top_left_p2_clamps_lower_bound():
    game = Game(board_size=6)
    game.current_player_id = PLAYER_2
    # A 3x3 piece with bottom-right at (0, 0) would go negative; clamp to fit.
    assert compute_top_left(game, w=3, h=3, cell=(0, 0)) == (0, 0)
