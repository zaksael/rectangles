from rectangles.bot import choose_placement
from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.game import Game


class ScriptedRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def test_choose_placement_returns_a_legal_candidate():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3, 0]))
    game.roll_dice()

    top_left, w, h = choose_placement(game)

    assert top_left in game.legal_cache.get((w, h), set())


def test_choose_placement_is_deterministic_via_rng_index():
    game = Game(board_size=6, rng=ScriptedRandom([2, 3, 0]))
    game.roll_dice()
    candidates = sorted(
        (top_left, w, h) for (w, h), top_lefts in game.legal_cache.items() for top_left in top_lefts
    )

    assert choose_placement(game) == candidates[0]


def test_choose_placement_greedy_prefers_capturing_a_flag():
    game = Game(board_size=6, flag_conquest_enabled=True, rng=ScriptedRandom([1, 1]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()

    assert choose_placement(game, "Greedy") == ((3, 3), 1, 1)


def test_choose_placement_greedy_falls_back_to_random_without_flags():
    game = Game(board_size=6, rng=ScriptedRandom([1, 1, 0]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()

    top_left, w, h = choose_placement(game, "Greedy")

    assert top_left in game.legal_cache.get((w, h), set())


def test_choose_placement_blocking_prefers_denying_opponent_frontier():
    game = Game(board_size=6, rng=ScriptedRandom([1, 1]))
    game.board.place(game.players[PLAYER_1], (2, 2), 1, 1)
    game.board.place(game.players[PLAYER_2], (2, 4), 1, 1)
    game.roll_dice()

    assert choose_placement(game, "Blocking") == ((2, 3), 1, 1)
