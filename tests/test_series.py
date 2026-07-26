from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.series import Series


def test_record_game_increments_winner_and_games_played():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(PLAYER_1)

    assert series.wins[PLAYER_1] == 1
    assert series.wins[PLAYER_2] == 0
    assert series.games_played == 1


def test_record_tied_game_only_increments_games_played():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(None)

    assert series.wins == {PLAYER_1: 0, PLAYER_2: 0}
    assert series.games_played == 1


def test_best_of_3_completes_after_two_wins_not_three_games():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(PLAYER_1)
    assert not series.is_complete()
    series.record_game(PLAYER_1)

    assert series.is_complete()
    assert series.games_played == 2
    assert series.winner() == PLAYER_1


def test_best_of_5_needs_three_wins():
    series = Series(length=5, board_size=6, skip_limit=2)

    series.record_game(PLAYER_1)
    series.record_game(PLAYER_2)
    series.record_game(PLAYER_1)
    assert not series.is_complete()
    series.record_game(PLAYER_1)

    assert series.is_complete()
    assert series.winner() == PLAYER_1


def test_series_completes_after_all_games_played_without_majority():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(None)
    series.record_game(None)
    series.record_game(None)

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
