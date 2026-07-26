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
