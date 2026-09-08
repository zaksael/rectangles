from rectangles.constants import PRIZE_BONUS_POINTS, PLAYER_1, PLAYER_2, CellKind
from rectangles.game import Game
from rectangles.series import Series

BOARD_SIZE = 40  # large enough that any fabricated area below fits in one strip


def _finished_game(
    p1_area: int, p1_prizes: int, p2_area: int, p2_prizes: int, prize_bonus_points: int = PRIZE_BONUS_POINTS
) -> Game:
    game = Game(board_size=BOARD_SIZE, special_cell_points={"prize": prize_bonus_points})
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    if p1_area:
        game.board.place(p1, (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(p2, (0, 0), p2_area, 1)
    p1.special_captures[CellKind.PRIZE] = p1_prizes
    p2.special_captures[CellKind.PRIZE] = p2_prizes
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


def test_record_game_stores_area_and_prizes_breakdown_per_round():
    series = Series(length=3, board_size=6, skip_limit=2, prize_enabled=True, special_cell_points={"prize": 10})

    series.record_game(_finished_game(8, 2, 4, 0, prize_bonus_points=10))

    assert len(series.rounds) == 1
    result = series.rounds[0]
    assert result.area == {PLAYER_1: 8, PLAYER_2: 4}
    assert result.prize_captured == {PLAYER_1: 2, PLAYER_2: 0}
    assert result.total == {PLAYER_1: 28, PLAYER_2: 4}
    assert series.scores == {PLAYER_1: 28, PLAYER_2: 4}


def test_total_prize_captured_sums_across_rounds():
    series = Series(length=3, board_size=6, skip_limit=2, prize_enabled=True, special_cell_points={"prize": 10})

    series.record_game(_finished_game(8, 2, 4, 0, prize_bonus_points=10))
    series.record_game(_finished_game(3, 0, 2, 1, prize_bonus_points=10))

    assert series.total_prize_captured(PLAYER_1) == 2
    assert series.total_prize_captured(PLAYER_2) == 1


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


def test_new_game_uses_series_prize_settings():
    series = Series(length=5, board_size=11, skip_limit=4, prize_enabled=True, special_cell_points={"prize": 20})

    game = series.new_game()

    assert game.prize_enabled is True
    assert game.points_for(CellKind.PRIZE) == 20


def test_new_game_uses_series_comeback_nudge_setting():
    series = Series(length=5, board_size=11, skip_limit=4, comeback_nudge_enabled=True)

    game = series.new_game()

    assert game.comeback_nudge_enabled is True


def test_new_game_uses_series_pitfall_settings():
    series = Series(length=5, board_size=11, skip_limit=4, pitfall_enabled=True, special_cell_points={"pitfall": 25})

    game = series.new_game()

    assert game.pitfall_enabled is True
    assert game.points_for(CellKind.PITFALL) == 25


def test_new_game_defaults_prize_disabled():
    series = Series(length=3, board_size=11, skip_limit=2)

    game = series.new_game()

    assert game.prize_enabled is False


def test_new_game_alternates_starting_player_by_round():
    series = Series(length=3, board_size=11, skip_limit=2)

    assert series.new_game().current_player_id == PLAYER_1

    series.record_game(_finished_game(1, 0, 0, 0))
    assert series.new_game().current_player_id == PLAYER_2

    series.record_game(_finished_game(1, 0, 0, 0))
    assert series.new_game().current_player_id == PLAYER_1
