import json

from rectangles import persistence
from rectangles.constants import FLAG_BONUS_POINTS, PLAYER_1, PLAYER_2
from rectangles.game import Game, GameOverReason, TurnState
from rectangles.series import Series


class ScriptedRandom:
    """Stand-in for random.Random that returns a fixed, ordered sequence."""

    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def test_round_trip_preserves_fresh_game(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)

    persistence.save_game(game, path=path)
    result = persistence.load_game(path)

    assert result is not None
    loaded, loaded_series = result
    assert loaded_series is None
    assert loaded.board_size == 6
    assert loaded.skip_limit == 2
    assert loaded.current_player_id == PLAYER_1
    assert loaded.state == TurnState.AWAITING_ROLL
    assert loaded.last_roll is None
    assert loaded.history == []
    assert loaded.players[PLAYER_1].pieces == []
    assert loaded.players[PLAYER_2].pieces == []


def test_round_trip_preserves_choosing_placement_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.state == TurnState.CHOOSING_PLACEMENT
    assert loaded.last_roll == (2, 3)
    assert loaded.legal_cache
    assert (2, 3) in loaded.legal_cache
    assert loaded.legal_cache[(2, 3)] == game.legal_cache[(2, 3)]


def test_round_trip_preserves_pieces_and_grid(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    p1 = game.players[PLAYER_1]
    p2 = game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=2, h=3)
    game.board.place(p2, (3, 3), w=2, h=2)

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    loaded_p1 = loaded.players[PLAYER_1]
    loaded_p2 = loaded.players[PLAYER_2]
    assert [(r.top_left, r.width, r.height) for r in loaded_p1.pieces] == [((0, 0), 2, 3)]
    assert [(r.top_left, r.width, r.height) for r in loaded_p2.pieces] == [((3, 3), 2, 2)]
    for r in range(0, 3):
        for c in range(0, 2):
            assert loaded.board.owner_at(r, c) == PLAYER_1
    for r in range(3, 5):
        for c in range(3, 5):
            assert loaded.board.owner_at(r, c) == PLAYER_2
    assert loaded.board.owner_at(4, 0) is None


def test_round_trip_preserves_skip_history_and_consecutive_skips(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty

    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    assert p1.consecutive_skips == 1

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.players[PLAYER_1].consecutive_skips == 1
    assert len(loaded.history) == 1
    record = loaded.history[0]
    assert record.player_id == PLAYER_1
    assert record.roll == (6, 6)
    assert record.placed is None


def test_round_trip_preserves_game_over_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=8, skip_limit=1)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    game.board.place(p1, (0, 0), w=1, h=1)
    game.board.place(p2, (7, 7), w=1, h=1)
    p1.consecutive_skips = 1
    assert game.check_game_over() is True

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.state == TurnState.GAME_OVER
    assert loaded.game_over_reason == GameOverReason.SKIP_LIMIT
    assert loaded.skipped_out_player_id == PLAYER_1
    assert loaded.blocked_player_id is None
    assert loaded.surrendered_player_id is None


def test_round_trip_preserves_flag_conquest_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, flag_conquest_enabled=True, flag_bonus_points=20, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag (5, 5)
    p1 = game.players[PLAYER_1]
    assert p1.flags_captured == 1

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.flag_conquest_enabled is True
    assert loaded.flag_bonus_points == 20
    assert loaded.board.flag_cells == {(0, 10), (10, 0), (5, 5)}
    assert loaded.players[PLAYER_1].flags_captured == 1
    assert loaded.total_score(loaded.players[PLAYER_1]) == p1.total_area + 20


def test_load_game_old_format_without_flag_keys_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["flag_conquest_enabled"]
    del data["flag_bonus_points"]
    for player_data in data["players"].values():
        del player_data["flags_captured"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.flag_conquest_enabled is False
    assert loaded.flag_bonus_points == FLAG_BONUS_POINTS
    assert loaded.players[PLAYER_1].flags_captured == 0
    assert loaded.players[PLAYER_2].flags_captured == 0


def test_round_trip_preserves_series(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    series = Series(length=5, board_size=6, skip_limit=2, flag_conquest_enabled=True, flag_bonus_points=20)
    series.record_game(PLAYER_1)
    series.record_game(PLAYER_2)

    persistence.save_game(game, series=series, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is not None
    assert loaded_series.length == 5
    assert loaded_series.board_size == 6
    assert loaded_series.skip_limit == 2
    assert loaded_series.flag_conquest_enabled is True
    assert loaded_series.flag_bonus_points == 20
    assert loaded_series.wins == {PLAYER_1: 1, PLAYER_2: 1}
    assert loaded_series.games_played == 2


def test_load_game_old_format_without_series_key_loads_as_no_series(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["series"]  # simulates a save file written before series support existed
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, loaded_series = result
    assert loaded_series is None
    assert loaded.board_size == 6


def test_load_game_missing_file_returns_none(tmp_path):
    assert persistence.load_game(tmp_path / "does_not_exist.json") is None


def test_load_game_empty_file_returns_none(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("")
    assert persistence.load_game(path) is None


def test_load_game_corrupt_json_returns_none(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{not valid json")
    assert persistence.load_game(path) is None


def test_load_game_non_dict_json_returns_none(tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps([1, 2, 3]))
    assert persistence.load_game(path) is None


def test_load_game_wrong_version_returns_none(tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({"version": 999}))
    assert persistence.load_game(path) is None


def test_has_save_and_delete_save(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=4)

    assert persistence.has_save(path) is False
    persistence.save_game(game, path=path)
    assert persistence.has_save(path) is True
    persistence.delete_save(path)
    assert persistence.has_save(path) is False


def test_delete_save_missing_file_does_not_raise(tmp_path):
    persistence.delete_save(tmp_path / "does_not_exist.json")


def test_save_game_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "dir" / "save.json"
    game = Game(board_size=4)

    persistence.save_game(game, path=path)

    assert path.exists()
    assert persistence.load_game(path) is not None


def test_has_game_in_progress():
    assert persistence.has_game_in_progress(None) is False

    game = Game(board_size=4, rng=ScriptedRandom([2, 2]))
    assert persistence.has_game_in_progress(game) is False  # no history yet

    game.roll_dice()
    game.attempt_place((0, 0), 2, 2)
    assert persistence.has_game_in_progress(game) is True

    game.state = TurnState.GAME_OVER
    assert persistence.has_game_in_progress(game) is False


def test_should_save_on_exit_true_while_game_in_progress():
    game = Game(board_size=4, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    game.attempt_place((0, 0), 2, 2)
    assert persistence.should_save_on_exit(game, series=None) is True


def test_should_save_on_exit_false_for_finished_game_no_series():
    game = Game(board_size=4)
    game.state = TurnState.GAME_OVER
    assert persistence.should_save_on_exit(game, series=None) is False


def test_should_save_on_exit_true_for_finished_round_mid_series():
    # A round just ended (state == GAME_OVER, no fresh history yet for the
    # next round) but the series itself isn't decided - must still save so
    # the series tally survives quitting from the game-over screen.
    game = Game(board_size=4)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=4, skip_limit=3)
    series.record_game(PLAYER_1)

    assert persistence.should_save_on_exit(game, series) is True


def test_should_save_on_exit_false_once_series_is_complete():
    game = Game(board_size=4)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=4, skip_limit=3)
    series.record_game(PLAYER_1)
    series.record_game(PLAYER_1)  # clinches best-of-3

    assert persistence.should_save_on_exit(game, series) is False
