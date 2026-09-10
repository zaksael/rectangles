from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.series import Series
from rectangles.tournament import Bracket, Participant


class ScriptedRandom:
    """Stand-in for random.Random that returns a fixed, ordered sequence."""

    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def _participants(n: int) -> list[Participant]:
    return [Participant(name=f"Player {i + 1}") for i in range(n)]


def _finished_series(series: Series, p1_area: int, p2_area: int) -> None:
    # Mirrors tests/test_series.py's _finished_game fabrication: fake a
    # completed round without playing one out.
    from rectangles.game import Game

    game = Game(board_size=40)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    if p1_area:
        game.board.place(p1, (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(p2, (0, 0), p2_area, 1)
    series.record_game(game)


def test_bracket_threads_comeback_nudge_setting_into_series_and_tiebreak_game():
    bracket = Bracket(
        participants=_participants(2),
        series_length=3,
        board_size=11,
        skip_limit=4,
        comeback_nudge_enabled=True,
    )

    series = bracket.new_series_for_current_match()
    assert series.comeback_nudge_enabled is True

    game = bracket.new_tiebreak_game()
    assert game.comeback_nudge_enabled is True


def test_bracket_threads_steal_setting_into_series_and_tiebreak_game():
    bracket = Bracket(
        participants=_participants(2),
        series_length=3,
        board_size=11,
        skip_limit=4,
        steal_enabled=True,
    )

    assert bracket.new_series_for_current_match().steal_enabled is True
    assert bracket.new_tiebreak_game().steal_enabled is True


def test_seeding_pairs_every_participant_exactly_once():
    # No shuffling (identity permutation): randint always returns the
    # untouched index i, so order == [0, 1, 2, 3].
    bracket = Bracket(
        participants=_participants(4),
        series_length=3,
        board_size=6,
        skip_limit=2,
        rng=ScriptedRandom([0, 1, 2]),
    )

    assert len(bracket.rounds) == 1
    matches = bracket.rounds[0]
    assert len(matches) == 2
    seen = sorted(m.participant_a for m in matches) + sorted(m.participant_b for m in matches)
    assert sorted(seen) == [0, 1, 2, 3]


def test_bracket_advances_through_full_8_participant_tree_to_a_champion():
    bracket = Bracket(
        participants=_participants(8),
        series_length=3,
        board_size=6,
        skip_limit=2,
        rng=ScriptedRandom([0, 1, 2, 3, 4, 5, 6]),
    )
    assert len(bracket.rounds[0]) == 4

    total_matches_played = 0
    while not bracket.is_complete():
        match = bracket.current_match()
        series = bracket.new_series_for_current_match()
        _finished_series(series, p1_area=10, p2_area=1)  # participant_a (PLAYER_1) always wins
        bracket.record_match_result()
        assert match.winner == match.participant_a
        bracket.advance()
        total_matches_played += 1

    assert total_matches_played == 7  # 4 + 2 + 1
    assert bracket.champion() is not None


def test_tied_series_requires_a_tiebreak_game_before_the_match_resolves():
    bracket = Bracket(participants=_participants(4), series_length=3, board_size=6, skip_limit=2)
    match = bracket.current_match()
    series = bracket.new_series_for_current_match()
    _finished_series(series, p1_area=5, p2_area=5)
    assert series.winner() is None

    bracket.record_match_result()
    assert match.winner is None  # no tiebreak game yet - nothing to resolve with

    from rectangles.game import Game

    tiebreak = Game(board_size=6)
    tiebreak.board.place(tiebreak.players[PLAYER_1], (0, 0), 3, 1)
    match.tiebreak_game = tiebreak

    bracket.record_match_result()
    assert match.winner == match.participant_a


def test_tied_tiebreak_game_breaks_via_coin_flip():
    bracket = Bracket(
        participants=_participants(4),
        series_length=3,
        board_size=6,
        skip_limit=2,
        rng=ScriptedRandom([0, 1, 2, 1]),  # 3 seeding picks, then the coin flip -> PLAYER_2
    )
    match = bracket.current_match()
    series = bracket.new_series_for_current_match()
    _finished_series(series, p1_area=5, p2_area=5)

    from rectangles.game import Game

    tiebreak = Game(board_size=6)  # both players score 0 - exact tie
    match.tiebreak_game = tiebreak

    bracket.record_match_result()
    assert match.winner == match.participant_b


def test_is_complete_and_champion_false_until_final_match_decided():
    bracket = Bracket(participants=_participants(4), series_length=3, board_size=6, skip_limit=2)
    assert not bracket.is_complete()
    assert bracket.champion() is None

    match = bracket.current_match()
    series = bracket.new_series_for_current_match()
    _finished_series(series, p1_area=10, p2_area=1)
    bracket.record_match_result()
    bracket.advance()
    assert not bracket.is_complete()  # round 1 has a second match still pending

    match = bracket.current_match()
    series = bracket.new_series_for_current_match()
    _finished_series(series, p1_area=10, p2_area=1)
    bracket.record_match_result()
    bracket.advance()
    assert len(bracket.rounds) == 2  # final round built
    assert not bracket.is_complete()

    match = bracket.current_match()
    series = bracket.new_series_for_current_match()
    _finished_series(series, p1_area=10, p2_area=1)
    bracket.record_match_result()
    bracket.advance()
    assert bracket.is_complete()
    assert bracket.champion() is bracket.participants[match.winner]
