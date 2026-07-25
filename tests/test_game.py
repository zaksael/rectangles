from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.game import Game, TurnState


class ScriptedRandom:
    """Stand-in for random.Random that returns a fixed, ordered sequence."""

    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def test_deterministic_roll_via_injected_rng():
    game = Game(rng=ScriptedRandom([4, 6]))
    assert game.roll_dice() == (4, 6)


def test_turn_alternates_after_placement():
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.attempt_place((0, 0), 2, 2) is True

    if not game.check_game_over():
        game.end_turn()

    assert game.current_player_id == PLAYER_2
    assert game.state == TurnState.AWAITING_ROLL


def test_skip_when_no_legal_move():
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty

    game.roll_dice()

    assert game.state == TurnState.SKIPPED
    assert game.last_roll == (6, 6)


def test_game_over_detection_after_placement():
    game = Game(board_size=2, rng=ScriptedRandom([1, 1, 1, 1, 1, 1, 1, 1]))

    game.roll_dice()
    assert game.attempt_place((0, 0), 1, 1) is True  # p1 anchors at (0,0)
    assert game.check_game_over() is False
    game.end_turn()

    game.roll_dice()
    assert game.attempt_place((1, 1), 1, 1) is True  # p2 anchors at (1,1)
    assert game.check_game_over() is False
    game.end_turn()

    game.roll_dice()
    assert game.attempt_place((0, 1), 1, 1) is True  # p1 claims (0,1)
    assert game.check_game_over() is False
    game.end_turn()

    game.roll_dice()
    assert game.attempt_place((1, 0), 1, 1) is True  # p2 claims the last cell
    assert game.check_game_over() is True
    assert game.state == TurnState.GAME_OVER


def test_game_over_detection_after_skip():
    game = Game(board_size=2, rng=ScriptedRandom([3, 3]))
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=2)
    game.board.place(p2, (0, 1), w=1, h=2)  # board fully filled

    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert game.check_game_over() is True


def test_winner_area_sum():
    game = Game(board_size=8)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=3, h=2)  # area 6
    game.board.place(p2, (6, 6), w=2, h=2)  # area 4
    assert game.winner() == PLAYER_1


def test_tie_returns_none():
    game = Game(board_size=8)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=2, h=2)  # area 4
    game.board.place(p2, (6, 6), w=2, h=2)  # area 4
    assert game.winner() is None


def test_degenerate_1x1_board_immediate_gameover():
    game = Game(board_size=1, rng=ScriptedRandom([1, 1]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    assert game.attempt_place((0, 0), 1, 1) is True
    assert game.check_game_over() is True
    assert game.winner() == PLAYER_1
