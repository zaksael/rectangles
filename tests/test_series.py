from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.series import Series


def test_record_game_accumulates_both_players_scores():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(10, 4)

    assert series.scores[PLAYER_1] == 10
    assert series.scores[PLAYER_2] == 4
    assert series.games_played == 1

    series.record_game(3, 12)

    assert series.scores[PLAYER_1] == 13
    assert series.scores[PLAYER_2] == 16
    assert series.games_played == 2


def test_series_not_complete_until_all_rounds_played_regardless_of_score_gap():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(30, 0)
    assert not series.is_complete()
    series.record_game(30, 0)
    assert not series.is_complete()
    series.record_game(0, 1)

    assert series.is_complete()
    assert series.games_played == 3


def test_trailing_round_winner_can_still_win_series_on_points():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(1, 0)
    series.record_game(0, 1)
    series.record_game(2, 20)

    assert series.is_complete()
    assert series.winner() == PLAYER_2


def test_series_tied_on_cumulative_score_after_all_rounds():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(5, 5)
    series.record_game(3, 3)
    series.record_game(2, 2)

    assert series.is_complete()
    assert series.winner() is None


def test_new_game_uses_series_settings():
    series = Series(length=5, board_size=8, skip_limit=4, doubles_enabled=True)

    game = series.new_game()

    assert game.board_size == 8
    assert game.skip_limit == 4
    assert game.doubles_enabled is True


def test_new_game_uses_series_flag_conquest_settings():
    series = Series(length=5, board_size=11, skip_limit=4, flag_conquest_enabled=True, flag_bonus_points=20)

    game = series.new_game()

    assert game.flag_conquest_enabled is True
    assert game.flag_bonus_points == 20


def test_new_game_defaults_flag_conquest_disabled():
    series = Series(length=3, board_size=11, skip_limit=2)

    game = series.new_game()

    assert game.flag_conquest_enabled is False
