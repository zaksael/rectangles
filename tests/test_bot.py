from rectangles.bot import choose_placement, choose_wildcard_value, should_reroll
from rectangles.constants import PLAYER_1, PLAYER_2, REROLL_LIMIT, CellKind
from rectangles.game import Game
from rectangles.models import Cell, SpecialCell


class ScriptedRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def _prizes(*cells: tuple[int, int]) -> frozenset[SpecialCell]:
    return frozenset(SpecialCell(CellKind.PRIZE, Cell(*cell), pair_id=i) for i, cell in enumerate(cells))


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


def test_choose_placement_greedy_prefers_capturing_a_prize():
    game = Game(board_size=6, rng=ScriptedRandom([1, 1]))
    game.prize_enabled = True
    game.board.special_cells = _prizes((3, 3))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()

    assert choose_placement(game, "Greedy") == ((3, 3), 1, 1)


def test_choose_placement_greedy_falls_back_to_blocking_score_without_prizes():
    # No Prize -> cell_overlap_score ties at 0 for every candidate; Greedy
    # should fall back to denying the opponent's frontier instead of a bare
    # random pick.
    game = Game(board_size=6, rng=ScriptedRandom([1, 1]))
    game.board.place(game.players[PLAYER_1], (2, 2), 1, 1)
    game.board.place(game.players[PLAYER_2], (2, 4), 1, 1)
    game.roll_dice()

    assert choose_placement(game, "Greedy") == ((2, 3), 1, 1)


def test_choose_placement_blocking_prefers_denying_opponent_frontier():
    game = Game(board_size=6, rng=ScriptedRandom([1, 1]))
    game.board.place(game.players[PLAYER_1], (2, 2), 1, 1)
    game.board.place(game.players[PLAYER_2], (2, 4), 1, 1)
    game.roll_dice()

    assert choose_placement(game, "Blocking") == ((2, 3), 1, 1)


def test_blocking_score_fn_computes_frontier_once_per_call_not_per_candidate():
    # Regression test: board.frontier() is a full grid scan: computing it inside
    # the per-candidate scoring lambda (instead of once, hoisted, per choose_*
    # call) turns an O(size^2) cost into O(candidates * size^2).
    game = Game(board_size=6, rng=ScriptedRandom([1, 1]))
    game.board.place(game.players[PLAYER_1], (2, 2), 1, 1)
    game.board.place(game.players[PLAYER_2], (2, 4), 1, 1)
    game.roll_dice()
    assert len(game.legal_cache[(1, 1)]) > 1  # a per-candidate bug needs >1 candidate to show

    calls = []
    real_frontier = game.board.frontier
    game.board.frontier = lambda player: (calls.append(player), real_frontier(player))[1]

    choose_placement(game, "Blocking")

    assert len(calls) == 1


def test_choose_wildcard_value_greedy_prefers_a_prize_capturing_value():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([2, 2, 0]))
    game.board.place(game.players[PLAYER_1], (2, 2), 1, 1)
    game.board.special_cells = _prizes((2, 5))
    game.roll_dice()
    assert game.state.name == "CHOOSING_WILDCARD"

    assert choose_wildcard_value(game, "Greedy") == 3


def test_choose_wildcard_value_blocking_prefers_a_frontier_denying_value():
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([1, 1, 0, 0]))
    game.board.place(game.players[PLAYER_1], (0, 0), 1, 1)
    game.board.place(game.players[PLAYER_2], (0, 5), 1, 1)
    game.roll_dice()
    assert game.state.name == "CHOOSING_WILDCARD"

    assert choose_wildcard_value(game, "Blocking") == 4


def test_choose_wildcard_value_greedy_prefers_the_larger_piece_without_a_prize():
    # No Prize -> cell_overlap_score ties at 0 for every legal value; unlike
    # choose_placement (one turn = one fixed w*h), different wildcard values
    # give different piece sizes, so Greedy should break the tie toward area.
    game = Game(board_size=8, wildcard_enabled=True, rng=ScriptedRandom([2, 2, 0]))
    game.board.place(game.players[PLAYER_1], (3, 3), 1, 1)
    game.roll_dice()
    assert game.state.name == "CHOOSING_WILDCARD"

    assert choose_wildcard_value(game, "Greedy") == 6


def test_should_reroll_at_zero_score_blocking_true_greedy_false_without_prize():
    # Blocking rerolls on a plain 0 score; Greedy doesn't - its cell_overlap_score is
    # structurally 0 without Prize on, so 0 isn't a signal for it -
    # see the guard test below for the prizes-exist-but-unreachable case.
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([1, 1, 0]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()
    assert game.state.name == "CHOOSING_PLACEMENT"

    assert should_reroll(game, "Blocking") is True
    assert should_reroll(game, "Greedy") is False


def test_should_reroll_true_for_greedy_when_prizes_exist_but_unreachable_this_turn():
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([1, 1, 0]))
    game.prize_enabled = True
    game.board.special_cells = _prizes((5, 5))
    game.board.place(game.players[PLAYER_1], (0, 0), 1, 1)
    game.roll_dice()
    assert game.state.name == "CHOOSING_PLACEMENT"
    prize_cells = game.board.cells_of_kind(CellKind.PRIZE)
    assert prize_cells  # sanity: prizes do exist this game
    assert not (prize_cells & {(0, 1), (1, 0)})  # ...just not reachable by this roll

    assert should_reroll(game, "Greedy") is True


def test_should_reroll_false_when_reroll_unavailable_even_at_zero_score():
    game = Game(board_size=6, reroll_enabled=False, rng=ScriptedRandom([1, 1, 0]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()

    assert should_reroll(game, "Greedy") is False


def test_should_reroll_false_when_reroll_charges_exhausted():
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([1, 1, 0]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.players[PLAYER_1].rerolls_used = REROLL_LIMIT
    game.roll_dice()

    assert should_reroll(game, "Greedy") is False


def test_should_reroll_false_for_basic_even_at_zero_score():
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([1, 1, 0]))
    game.board.place(game.players[PLAYER_1], (2, 3), 1, 1)
    game.roll_dice()

    assert should_reroll(game, "Basic") is False


def test_should_reroll_true_when_skipped_and_reroll_available():
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    assert game.state.name == "SKIPPED"

    assert should_reroll(game, "Greedy") is True


def test_should_reroll_true_when_every_wildcard_value_scores_zero():
    # Blocking, not Greedy - see the guard tests above.
    game = Game(board_size=6, wildcard_enabled=True, reroll_enabled=True, rng=ScriptedRandom([5, 5, 0]))
    game.roll_dice()
    assert game.state.name == "CHOOSING_WILDCARD"

    assert should_reroll(game, "Blocking") is True
