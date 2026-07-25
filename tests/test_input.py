import pygame

from rectangles.constants import PLAYER_2
from rectangles.game import Game, TurnState
from rectangles.ui.input import compute_top_left, handle_event
from rectangles.ui.state import ConfirmAction, Screen, UIState


class ScriptedRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def test_compute_top_left_p1_uses_cell_directly():
    game = Game(board_size=6)
    assert compute_top_left(game, w=2, h=2, cell=(2, 3)) == (2, 3)


def test_compute_top_left_p1_clamps_upper_bound():
    game = Game(board_size=6)
    # A 2x2 piece anchored at (5, 5) would overrun the board; clamp to fit.
    assert compute_top_left(game, w=2, h=2, cell=(5, 5)) == (4, 4)


def test_compute_top_left_p2_uses_cell_as_bottom_right():
    game = Game(board_size=6)
    game.current_player_id = PLAYER_2
    # A 2x2 piece with bottom-right at (5, 5) has top-left at (4, 4).
    assert compute_top_left(game, w=2, h=2, cell=(5, 5)) == (4, 4)


def test_compute_top_left_p2_clamps_lower_bound():
    game = Game(board_size=6)
    game.current_player_id = PLAYER_2
    # A 3x3 piece with bottom-right at (0, 0) would go negative; clamp to fit.
    assert compute_top_left(game, w=3, h=3, cell=(0, 0)) == (0, 0)


def _played_game() -> Game:
    game = Game(board_size=6, rng=ScriptedRandom([2, 2]))
    game.roll_dice()
    game.attempt_place((0, 0), 2, 2)
    return game


def test_new_game_key_without_history_resets_immediately():
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.SETTINGS


def test_new_game_key_with_history_requests_confirmation():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation == ConfirmAction.NEW_GAME
    assert ui_state.screen == Screen.PLAYING


def test_confirm_new_game_with_enter_performs_reset():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.SETTINGS


def test_cancel_new_game_with_escape_leaves_state_untouched():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.NEW_GAME)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation is None
    assert ui_state.screen == Screen.PLAYING
    assert len(game.history) == 1


def test_quit_mid_match_with_history_requests_confirmation():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.QUIT)

    assert handle_event(event, game, ui_state) is True

    assert ui_state.pending_confirmation == ConfirmAction.EXIT


def test_quit_without_history_returns_false_immediately():
    game = Game(board_size=6)
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.QUIT)

    assert handle_event(event, game, ui_state) is False
    assert ui_state.pending_confirmation is None


def test_quit_after_game_over_returns_false_immediately():
    game = _played_game()
    game.state = TurnState.GAME_OVER
    ui_state = UIState(screen=Screen.PLAYING)
    event = pygame.event.Event(pygame.QUIT)

    assert handle_event(event, game, ui_state) is False
    assert ui_state.pending_confirmation is None


def test_confirm_exit_with_enter_returns_false():
    game = _played_game()
    ui_state = UIState(screen=Screen.PLAYING, pending_confirmation=ConfirmAction.EXIT)
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)

    assert handle_event(event, game, ui_state) is False
