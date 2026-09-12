import pygame

from rectangles.constants import PLAYER_1
from rectangles.game import TurnState
from rectangles.ui import layout
from rectangles.ui.app import _connect_query_params, _new_game
from rectangles.ui.input import handle_event
from rectangles.ui.net_adapter import ServerGameAdapter
from rectangles.ui.state import Screen, UIState
from server.app import run_in_background


def test_connect_query_params_excludes_wildcard_and_reroll():
    # Not proxied through the adapter at all - see _HOUSE_RULE_QUERY_PARAMS.
    ui_state = UIState(selected_wildcard_enabled=True, selected_reroll_enabled=True)
    params = _connect_query_params(ui_state)
    assert "wildcardEnabled" not in params
    assert "rerollEnabled" not in params


def test_connect_query_params_includes_walls_enabled():
    ui_state = UIState(selected_walls_enabled=True)
    assert _connect_query_params(ui_state)["wallsEnabled"] == "true"


def test_connect_query_params_includes_obstacles_enabled():
    ui_state = UIState(selected_obstacles_enabled=True)
    assert _connect_query_params(ui_state)["obstaclesEnabled"] == "true"


def test_connect_query_params_includes_prize_enabled():
    ui_state = UIState(selected_prize_enabled=True)
    assert _connect_query_params(ui_state)["prizeEnabled"] == "true"


def test_connect_query_params_includes_pitfall_enabled():
    ui_state = UIState(selected_pitfall_enabled=True)
    assert _connect_query_params(ui_state)["pitfallEnabled"] == "true"


def test_connect_query_params_includes_steal_enabled():
    ui_state = UIState(selected_steal_enabled=True)
    assert _connect_query_params(ui_state)["stealEnabled"] == "true"


def test_connect_query_params_includes_self_enclosed_penalty_enabled():
    ui_state = UIState(selected_self_enclosed_penalty_enabled=True)
    assert _connect_query_params(ui_state)["selfEnclosedPenaltyEnabled"] == "true"


def test_connect_query_params_includes_comeback_nudge_enabled():
    ui_state = UIState(selected_comeback_nudge_enabled=True)
    assert _connect_query_params(ui_state)["comebackNudgeEnabled"] == "true"


def test_new_game_over_the_wire_plays_a_full_turn():
    url, stop = run_in_background()
    try:
        ui_state = UIState(screen=Screen.PLAYING)
        game = _new_game(ui_state, url)
        try:
            assert isinstance(game, ServerGameAdapter)

            assert handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d), game, ui_state) is True
            assert game.state == TurnState.CHOOSING_PLACEMENT

            entry = next(e for e in game.legal_cache.items() if e[1])
            (width, height), top_lefts = entry
            row, col = next(iter(top_lefts))
            pos = layout.cell_rect(row, col, board_size=game.board.size).center

            assert handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos), game, ui_state) is True

            assert len(game.players[PLAYER_1].pieces) == 1
        finally:
            game.close()
    finally:
        stop()
