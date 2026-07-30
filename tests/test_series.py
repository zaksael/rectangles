from rectangles.constants import FLAG_BONUS_POINTS, PLAYER_1, PLAYER_2
from rectangles.game import Game
from rectangles.series import Series

BOARD_SIZE = 40  # large enough that any fabricated area below fits in one strip


def _finished_game(
    p1_area: int, p1_flags: int, p2_area: int, p2_flags: int, flag_bonus_points: int = FLAG_BONUS_POINTS
) -> Game:
    game = Game(board_size=BOARD_SIZE, flag_bonus_points=flag_bonus_points)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    if p1_area:
        game.board.place(p1, (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(p2, (0, 0), p2_area, 1)
    p1.flags_captured = p1_flags
    p2.flags_captured = p2_flags
    return game


def test_record_game_accumulates_both_players_scores():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(_finished_game(10, 0, 4, 0))

    assert series.scores[PLAYER_1] == 10
    assert series.scores[PLAYER_2] == 4
    assert series.games_played == 1

    series.record_game(_finished_game(3, 0, 12, 0))

    assert series.scores[PLAYER_1] == 13
    assert series.scores[PLAYER_2] == 16
    assert series.games_played == 2


def test_record_game_stores_area_and_flags_breakdown_per_round():
    series = Series(length=3, board_size=6, skip_limit=2, flag_conquest_enabled=True, flag_bonus_points=10)

    series.record_game(_finished_game(8, 2, 4, 0, flag_bonus_points=10))

    assert len(series.rounds) == 1
    result = series.rounds[0]
    assert result.area == {PLAYER_1: 8, PLAYER_2: 4}
    assert result.flags_captured == {PLAYER_1: 2, PLAYER_2: 0}
    assert result.total == {PLAYER_1: 28, PLAYER_2: 4}
    assert series.scores == {PLAYER_1: 28, PLAYER_2: 4}


def test_total_flags_captured_sums_across_rounds():
    series = Series(length=3, board_size=6, skip_limit=2, flag_conquest_enabled=True, flag_bonus_points=10)

    series.record_game(_finished_game(8, 2, 4, 0, flag_bonus_points=10))
    series.record_game(_finished_game(3, 0, 2, 1, flag_bonus_points=10))

    assert series.total_flags_captured(PLAYER_1) == 2
    assert series.total_flags_captured(PLAYER_2) == 1


def test_series_not_complete_until_all_rounds_played_regardless_of_score_gap():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(_finished_game(30, 0, 0, 0))
    assert not series.is_complete()
    series.record_game(_finished_game(30, 0, 0, 0))
    assert not series.is_complete()
    series.record_game(_finished_game(0, 0, 1, 0))

    assert series.is_complete()
    assert series.games_played == 3


def test_trailing_round_winner_can_still_win_series_on_points():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(_finished_game(1, 0, 0, 0))
    series.record_game(_finished_game(0, 0, 1, 0))
    series.record_game(_finished_game(2, 0, 20, 0))

    assert series.is_complete()
    assert series.winner() == PLAYER_2


def test_series_tied_on_cumulative_score_after_all_rounds():
    series = Series(length=3, board_size=6, skip_limit=2)

    series.record_game(_finished_game(5, 0, 5, 0))
    series.record_game(_finished_game(3, 0, 3, 0))
    series.record_game(_finished_game(2, 0, 2, 0))

    assert series.is_complete()
    assert series.winner() is None


def test_new_game_uses_series_settings():
    series = Series(length=5, board_size=8, skip_limit=4)

    game = series.new_game()

    assert game.board_size == 8
    assert game.skip_limit == 4


def test_new_game_uses_series_flag_conquest_settings():
    series = Series(length=5, board_size=11, skip_limit=4, flag_conquest_enabled=True, flag_bonus_points=20)

    game = series.new_game()

    assert game.flag_conquest_enabled is True
    assert game.flag_bonus_points == 20


def test_new_game_defaults_flag_conquest_disabled():
    series = Series(length=3, board_size=11, skip_limit=2)

    game = series.new_game()

    assert game.flag_conquest_enabled is False
