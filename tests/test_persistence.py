import json

from rectangles import persistence
from rectangles.constants import (
    STEAL_POINTS,
    PRIZE_BONUS_POINTS,
    PITFALL_PENALTY_POINTS,
    PLAYER_1,
    PLAYER_2,
    CellKind,
)
from rectangles.game import Game, GameOverReason, TurnState
from rectangles.models import Cell, SpecialCell
from rectangles.series import Series


class ScriptedRandom:
    """Stand-in for random.Random that returns a fixed, ordered sequence."""

    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def _finished_game(board_size, p1_area, p2_area, p1_prizes=0, p2_prizes=0, prize_bonus_points=PRIZE_BONUS_POINTS):
    game = Game(board_size=board_size, special_cell_points={"prize": prize_bonus_points})
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    if p1_area:
        game.board.place(p1, (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(p2, (0, 0), p2_area, 1)
    p1.special_captures[CellKind.PRIZE] = p1_prizes
    p2.special_captures[CellKind.PRIZE] = p2_prizes
    return game


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


def test_round_trip_preserves_prize_state(tmp_path):
    path = tmp_path / "save.json"
    # prize_enabled stays False at construction to skip random
    # generation (and its rng consumption); flipped True with special_cells
    # set directly so the capture is deterministic.
    game = Game(board_size=11, special_cell_points={"prize": 20}, rng=ScriptedRandom([6, 6]))
    game.prize_enabled = True
    game.board.special_cells = frozenset(
        SpecialCell(CellKind.PRIZE, Cell(*cell), pair_id=i)
        for i, cell in enumerate([(0, 10), (10, 0), (5, 5)])
    )
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center prize (5, 5)
    p1 = game.players[PLAYER_1]
    assert p1.special_captures.get(CellKind.PRIZE, 0) == 1

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.prize_enabled is True
    assert loaded.points_for(CellKind.PRIZE) == 20
    assert loaded.board.cells_of_kind(CellKind.PRIZE) == {(0, 10), (10, 0), (5, 5)}
    assert loaded.players[PLAYER_1].special_captures.get(CellKind.PRIZE, 0) == 1
    assert loaded.total_score(loaded.players[PLAYER_1]) == p1.total_area + 20


def test_load_game_old_format_without_prize_keys_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["prize_enabled"]
    del data["special_cell_points"]
    for player_data in data["players"].values():
        del player_data["special_captures"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.prize_enabled is False
    assert loaded.points_for(CellKind.PRIZE) == PRIZE_BONUS_POINTS
    assert loaded.players[PLAYER_1].special_captures.get(CellKind.PRIZE, 0) == 0
    assert loaded.players[PLAYER_2].special_captures.get(CellKind.PRIZE, 0) == 0


def test_round_trip_preserves_walls_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, walls_enabled=True)
    wall_edges = game.board.wall_edges
    assert wall_edges != frozenset()

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.walls_enabled is True
    assert loaded.board.wall_edges == wall_edges


def test_load_game_old_format_without_walls_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["walls_enabled"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.walls_enabled is False
    assert loaded.board.wall_edges == frozenset()


def test_round_trip_preserves_obstacles_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, obstacles_enabled=True)
    obstacle_cells = game.board.obstacle_cells
    assert obstacle_cells != frozenset()

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.obstacles_enabled is True
    assert loaded.board.obstacle_cells == obstacle_cells
    # The loaded obstacle cells must actually be seeded into _grid, not just
    # tracked as metadata - a placement on one of them must stay illegal.
    for r, c in obstacle_cells:
        assert loaded.board.is_empty(r, c) is False


def test_load_game_old_format_without_obstacles_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["obstacles_enabled"]
    del data["obstacle_cells"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.obstacles_enabled is False
    assert loaded.board.obstacle_cells == frozenset()


def test_round_trip_preserves_pitfall_cells_state(tmp_path):
    path = tmp_path / "save.json"
    # pitfall_enabled stays False at construction to skip random
    # generation (and its rng consumption); flipped True with special_cells
    # set directly so the trigger is deterministic, same technique the prize
    # round-trip test above uses.
    game = Game(board_size=11, rng=ScriptedRandom([6, 6]))
    game.pitfall_enabled = True
    game.board.special_cells = frozenset({SpecialCell(CellKind.PITFALL, Cell(5, 5), pair_id=0)})
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # triggers the pitfall at (5, 5)
    p1 = game.players[PLAYER_1]
    assert p1.special_captures.get(CellKind.PITFALL, 0) == 1

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.pitfall_enabled is True
    assert loaded.points_for(CellKind.PITFALL) == PITFALL_PENALTY_POINTS
    assert loaded.board.cells_of_kind(CellKind.PITFALL) == {(5, 5)}
    assert loaded.players[PLAYER_1].special_captures.get(CellKind.PITFALL, 0) == 1
    assert loaded.total_score(loaded.players[PLAYER_1]) == p1.total_area - PITFALL_PENALTY_POINTS


def test_round_trip_preserves_steal_cells_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, rng=ScriptedRandom([6, 6]))
    game.steal_enabled = True
    game.board.special_cells = frozenset({SpecialCell(CellKind.STEAL, Cell(5, 5), pair_id=0)})
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the steal cell at (5, 5)
    p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
    assert p1.special_captures.get(CellKind.STEAL, 0) == 1

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.steal_enabled is True
    assert loaded.board.cells_of_kind(CellKind.STEAL) == {(5, 5)}
    assert loaded.players[PLAYER_1].special_captures.get(CellKind.STEAL, 0) == 1
    assert loaded.total_score(loaded.players[PLAYER_1]) == p1.total_area + STEAL_POINTS
    assert loaded.total_score(loaded.players[PLAYER_2]) == p2.total_area - STEAL_POINTS


def test_load_game_old_format_without_steal_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["steal_enabled"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.steal_enabled is False
    assert loaded.board.cells_of_kind(CellKind.STEAL) == frozenset()


def test_load_game_old_format_without_pitfall_cells_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["pitfall_enabled"]
    del data["special_cell_points"]
    del data["special_cells"]
    for player_data in data["players"].values():
        del player_data["special_captures"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.pitfall_enabled is False
    assert loaded.points_for(CellKind.PITFALL) == PITFALL_PENALTY_POINTS
    assert loaded.board.cells_of_kind(CellKind.PITFALL) == frozenset()
    assert loaded.players[PLAYER_1].special_captures.get(CellKind.PITFALL, 0) == 0
    assert loaded.players[PLAYER_2].special_captures.get(CellKind.PITFALL, 0) == 0


def test_round_trip_preserves_wildcard_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, wildcard_enabled=True)

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.wildcard_enabled is True


def test_load_game_old_format_without_wildcard_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["wildcard_enabled"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.wildcard_enabled is False


def test_round_trip_preserves_choosing_wildcard_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([5, 5, 0]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.state == TurnState.CHOOSING_WILDCARD
    assert loaded.wildcard_index == 0
    assert loaded.wildcard_original_roll == (5, 5)

    loaded.choose_wildcard_value(6)
    assert loaded.last_roll == (6, 5)
    assert loaded.state == TurnState.CHOOSING_PLACEMENT


def test_round_trip_preserves_self_enclosed_penalty_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, self_enclosed_penalty_enabled=True)

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.self_enclosed_penalty_enabled is True


def test_load_game_old_format_without_self_enclosed_penalty_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["self_enclosed_penalty_enabled"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.self_enclosed_penalty_enabled is False


def test_round_trip_preserves_reroll_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, reroll_enabled=True)
    game.players[PLAYER_1].rerolls_used = 1

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.reroll_enabled is True
    assert loaded.players[PLAYER_1].rerolls_used == 1


def test_load_game_old_format_without_reroll_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["reroll_enabled"]
    del data["players"][PLAYER_1]["rerolls_used"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.reroll_enabled is False
    assert loaded.players[PLAYER_1].rerolls_used == 0


def test_round_trip_preserves_comeback_nudge_state(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=11, comeback_nudge_enabled=True)
    game.players[PLAYER_1].comeback_nudge_granted = True

    persistence.save_game(game, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is None
    assert loaded.comeback_nudge_enabled is True
    assert loaded.players[PLAYER_1].comeback_nudge_granted is True


def test_load_game_old_format_without_comeback_nudge_key_defaults_disabled(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    data = persistence.to_dict(game)
    del data["comeback_nudge_enabled"]
    del data["players"][PLAYER_1]["comeback_nudge_granted"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    loaded, _ = result
    assert loaded.comeback_nudge_enabled is False
    assert loaded.players[PLAYER_1].comeback_nudge_granted is False


def test_round_trip_preserves_series(tmp_path):
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    series = Series(length=5, board_size=6, skip_limit=2, prize_enabled=True, special_cell_points={"prize": 20})
    series.record_game(_finished_game(12, 8, 4, p1_prizes=1, prize_bonus_points=20))
    series.record_game(_finished_game(12, 3, 12, prize_bonus_points=20))

    persistence.save_game(game, series=series, path=path)
    loaded, loaded_series = persistence.load_game(path)

    assert loaded_series is not None
    assert loaded_series.length == 5
    assert loaded_series.board_size == 6
    assert loaded_series.skip_limit == 2
    assert loaded_series.prize_enabled is True
    assert loaded_series.special_cell_points == {"prize": 20}
    assert loaded_series.scores == {PLAYER_1: 31, PLAYER_2: 16}
    assert loaded_series.games_played == 2
    assert loaded_series.rounds == series.rounds


def test_load_game_series_without_rounds_key_loads_with_empty_rounds(tmp_path):
    # Simulates a save written by the previous commit, before per-round history existed.
    path = tmp_path / "save.json"
    game = Game(board_size=6, skip_limit=2)
    series = Series(length=3, board_size=6, skip_limit=2)
    series.record_game(_finished_game(6, 5, 2))
    data = persistence.to_dict(game, series)
    del data["series"]["rounds"]
    path.write_text(json.dumps(data))

    result = persistence.load_game(path)

    assert result is not None
    _, loaded_series = result
    assert loaded_series is not None
    assert loaded_series.scores == {PLAYER_1: 5, PLAYER_2: 2}
    assert loaded_series.rounds == []


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
    series.record_game(_finished_game(4, 1, 0))

    assert persistence.should_save_on_exit(game, series) is True


def test_should_save_on_exit_false_once_series_is_complete():
    game = Game(board_size=4)
    game.state = TurnState.GAME_OVER
    series = Series(length=3, board_size=4, skip_limit=3)
    series.record_game(_finished_game(4, 1, 0))
    series.record_game(_finished_game(4, 1, 0))
    series.record_game(_finished_game(4, 1, 0))  # all 3 rounds played

    assert persistence.should_save_on_exit(game, series) is False
