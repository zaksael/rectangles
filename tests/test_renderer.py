import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.game import Game, GameOverReason, TurnState
from rectangles.series import Series
from rectangles.ui.renderer import Renderer
from rectangles.ui.state import ConfirmAction, Screen, UIState


class ScriptedRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def _finished_game(board_size, p1_area, p2_area):
    game = Game(board_size=board_size)
    if p1_area:
        game.board.place(game.players[PLAYER_1], (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(game.players[PLAYER_2], (0, 0), p2_area, 1)
    return game


@pytest.fixture(scope="module")
def renderer():
    pygame.init()
    screen = pygame.display.set_mode((100, 100))
    return Renderer(screen)


def test_draw_settings_screen_smoke(renderer):
    renderer.draw(None, UIState(screen=Screen.SETTINGS))


def test_draw_awaiting_roll_smoke(renderer):
    game = Game(board_size=6)
    renderer.draw(game, UIState(screen=Screen.PLAYING))


@pytest.mark.parametrize("hover_legal", [True, False])
def test_draw_choosing_placement_smoke(renderer, hover_legal):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    ui_state = UIState(
        screen=Screen.PLAYING, current_dims=(2, 3), hover_top_left=(0, 0), hover_legal=hover_legal
    )
    renderer.draw(game, ui_state)


def test_draw_skipped_smoke(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_flag_conquest_smoke(renderer):
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag, leaves 2 uncaptured
    if not game.check_game_over():
        game.end_turn()
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_walls_smoke(renderer):
    game = Game(board_size=11, walls_enabled=True)
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_last_move_highlight_smoke(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    if not game.check_game_over():
        game.end_turn()
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_last_placed_rect_none_before_any_history(renderer):
    game = Game(board_size=6)
    assert renderer._last_placed_rect(game) is None


def test_last_placed_rect_ignores_a_trailing_skip(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([2, 2, 6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()  # (6, 6) is too big for a 4x4 board regardless of state: guaranteed skip
    assert game.state == TurnState.SKIPPED

    last_placed = renderer._last_placed_rect(game)
    assert (last_placed.top_left, last_placed.width, last_placed.height) == ((0, 0), 2, 2)


def test_captured_flag_cells_none_without_flag_conquest(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    assert renderer._captured_flag_cells(game) == frozenset()


def test_captured_flag_cells_on_the_last_placement(renderer):
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag (5, 5)
    assert renderer._captured_flag_cells(game) == frozenset({(5, 5)})


def test_captured_flag_cells_ignores_earlier_placements(renderer):
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([6, 6, 4, 4]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag (5, 5)
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((7, 7), 4, 4) is True  # P2's start-corner anchor; no flag in this footprint
    assert renderer._captured_flag_cells(game) == frozenset()


def test_status_banner_message_none_on_a_normal_awaiting_roll(renderer):
    game = Game(board_size=6)
    assert renderer._status_banner_message(game) is None


def test_status_banner_message_on_skipped_turn(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty
    game.roll_dice()
    assert game.state == TurnState.SKIPPED

    assert renderer._status_banner_message(game) == "Player 1 skipped - no legal placement!"


def test_status_banner_message_on_doubles_bonus_turn(renderer):
    game = Game(board_size=6, doubles_enabled=True, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    assert game.state == TurnState.AWAITING_ROLL
    assert game.current_player_id == PLAYER_1  # doubles: same player continues

    assert renderer._status_banner_message(game) == "Doubles! Player 1 rolls again"


def test_draw_doubles_banner_smoke(renderer):
    game = Game(board_size=6, doubles_enabled=True, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    renderer.draw(game, UIState(screen=Screen.PLAYING))


@pytest.mark.parametrize(
    "reason",
    [
        GameOverReason.BOARD_FULL,
        GameOverReason.PLAYER_BLOCKED,
        GameOverReason.SKIP_LIMIT,
        GameOverReason.SURRENDER,
    ],
)
def test_draw_game_over_each_reason_smoke(renderer, reason):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = reason
    game.skipped_out_player_id = PLAYER_1
    game.blocked_player_id = PLAYER_2
    game.surrendered_player_id = PLAYER_1
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_game_over_tie_smoke(renderer):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_panel_with_series_stats_smoke(renderer):
    game = Game(board_size=6, flag_conquest_enabled=True)
    series = Series(length=3, board_size=6, skip_limit=3, flag_conquest_enabled=True, flag_bonus_points=10)
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


def test_panel_series_rows_shows_everything_when_it_fits(renderer):
    series = Series(length=3, board_size=6, skip_limit=3)
    for _ in range(3):
        series.record_game(_finished_game(6, 1, 0))

    rows, hidden = renderer._panel_series_rows(series)

    assert hidden == 0
    assert [row[0] for row in rows] == ["1", "2", "3", "Total"]


def test_panel_series_rows_truncates_to_most_recent_plus_totals(renderer):
    from rectangles.ui import layout

    series = Series(length=5, board_size=6, skip_limit=3)
    for _ in range(5):
        series.record_game(_finished_game(6, 1, 0))

    rows, hidden = renderer._panel_series_rows(series)

    assert hidden == 3
    assert len(rows) == layout.PANEL_SERIES_MAX_ROWS - 2
    assert [row[0] for row in rows] == ["4", "5", "Total"]


def test_draw_panel_with_a_full_five_round_series_smoke(renderer):
    # The worst case that PANEL_SERIES_MAX_ROWS/MIN_WINDOW_HEIGHT are sized for:
    # a maxed-out history log alongside a full 5-round Flag Conquest series.
    game = Game(board_size=6, flag_conquest_enabled=True)
    series = Series(length=5, board_size=6, skip_limit=3, flag_conquest_enabled=True, flag_bonus_points=20)
    for _ in range(5):
        series.record_game(_finished_game(6, 1, 0))
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


def test_draw_game_over_with_series_in_progress_smoke(renderer):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


def test_draw_game_over_with_series_complete_smoke(renderer):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))  # all 3 rounds played
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


@pytest.mark.parametrize("action", list(ConfirmAction))
def test_draw_confirm_dialog_each_action_smoke(renderer, action):
    game = Game(board_size=6)
    renderer.draw(game, UIState(screen=Screen.PLAYING, pending_confirmation=action))
