from __future__ import annotations

import pygame

from .. import persistence
from ..game import Game, TurnState
from ..series import Series
from ..tournament import Bracket
from . import layout
from .input_common import (
    _advance_or_end_series,
    _choose_wildcard_value,
    _design_pos,
    _new_game,
    _reroll,
    _roll_dice,
    _rotate,
    compute_top_left,
    continue_turn,
    is_bots_turn,
)
from .state import ConfirmAction, Screen, UIState


def _request_new_game(game: Game, ui_state: UIState) -> None:
    if game.history:
        ui_state.pending_confirmation = ConfirmAction.NEW_GAME
    else:
        _new_game(ui_state)


def _request_surrender(ui_state: UIState) -> None:
    ui_state.pending_confirmation = ConfirmAction.SURRENDER


def _request_quit(game: Game | None, ui_state: UIState) -> bool:
    if ui_state.screen == Screen.PLAYING and persistence.has_game_in_progress(game):
        ui_state.pending_confirmation = ConfirmAction.EXIT
        return True
    return False


def _handle_left_click(
    pos: tuple[int, int], game: Game, ui_state: UIState, series: Series | None, tournament: Bracket | None
) -> bool:
    if game.state == TurnState.GAME_OVER:
        if layout.GAME_OVER_NEW_GAME_BUTTON_RECT.collidepoint(pos):
            _advance_or_end_series(tournament, series, ui_state)
        elif layout.GAME_OVER_REPLAY_BUTTON_RECT.collidepoint(pos):
            ui_state.screen = Screen.REPLAY
            ui_state.replay_step = 0
            ui_state.replay_autoplay = False
        elif tournament is not None and layout.GAME_OVER_BRACKET_BUTTON_RECT.collidepoint(pos):
            ui_state.screen = Screen.TOURNAMENT
        elif layout.GAME_OVER_EXIT_BUTTON_RECT.collidepoint(pos):
            return False
        return True

    if layout.NEW_GAME_BUTTON_RECT.collidepoint(pos):
        _request_new_game(game, ui_state)
        return True

    if layout.EXIT_BUTTON_RECT.collidepoint(pos):
        return _request_quit(game, ui_state)

    if layout.SURRENDER_BUTTON_RECT.collidepoint(pos):
        _request_surrender(ui_state)
        return True

    if is_bots_turn(game, ui_state):
        return True

    if game.state == TurnState.AWAITING_ROLL:
        if layout.ROLL_BUTTON_RECT.collidepoint(pos):
            _roll_dice(game, ui_state)
        return True

    if game.state == TurnState.CHOOSING_WILDCARD:
        if game.can_reroll() and layout.REROLL_WILDCARD_BUTTON_RECT.collidepoint(pos):
            _reroll(game, ui_state)
            return True
        # Deliberately not gated on wildcard_value_is_legal() - the graying is
        # cosmetic, and roll_dice() guarantees at least one value is legal here.
        for value, rect in layout.WILDCARD_VALUE_BUTTON_RECTS.items():
            if rect.collidepoint(pos):
                _choose_wildcard_value(game, ui_state, value)
                break
        return True

    if game.state == TurnState.SKIPPED:
        if game.can_reroll():
            if layout.REROLL_SKIPPED_BUTTON_RECT.collidepoint(pos):
                _reroll(game, ui_state)
            elif layout.SKIP_BUTTON_RECT.collidepoint(pos):
                continue_turn(game)
        elif layout.CONTINUE_BUTTON_RECT.collidepoint(pos):
            continue_turn(game)
        return True

    if game.state == TurnState.CHOOSING_PLACEMENT:
        if layout.ROTATE_BUTTON_RECT.collidepoint(pos):
            _rotate(ui_state)
            return True
        if game.can_reroll() and layout.REROLL_PLACEMENT_BUTTON_RECT.collidepoint(pos):
            _reroll(game, ui_state)
            return True
        cell = layout.pixel_to_cell(*pos, game.board.size)
        if cell is None or ui_state.current_dims is None:
            return True
        w, h = ui_state.current_dims
        top_left = compute_top_left(game, w, h, cell)
        if game.attempt_place(top_left, w, h):
            if not game.check_game_over():
                game.end_turn()
            ui_state.reset()
        return True

    return True


def _handle_keydown(
    event: pygame.event.Event, game: Game, ui_state: UIState, series: Series | None, tournament: Bracket | None
) -> bool:
    if game.state == TurnState.GAME_OVER:
        if event.key == pygame.K_n:
            _advance_or_end_series(tournament, series, ui_state)
        elif event.key == pygame.K_ESCAPE:
            return False
        return True

    if event.key == pygame.K_n:
        _request_new_game(game, ui_state)
    elif event.key == pygame.K_ESCAPE:
        return _request_quit(game, ui_state)
    elif event.key == pygame.K_s:
        _request_surrender(ui_state)
    elif event.key == pygame.K_r and game.state == TurnState.CHOOSING_PLACEMENT and not is_bots_turn(
        game, ui_state
    ):
        _rotate(ui_state)
    elif event.key == pygame.K_d and game.state == TurnState.AWAITING_ROLL and not is_bots_turn(game, ui_state):
        _roll_dice(game, ui_state)
    elif event.key == pygame.K_SPACE and game.state == TurnState.SKIPPED and not is_bots_turn(game, ui_state):
        continue_turn(game)
    return True


def _resolve_confirmation(action: ConfirmAction | None, game: Game, ui_state: UIState) -> bool:
    if action == ConfirmAction.NEW_GAME:
        _new_game(ui_state)
        return True
    if action == ConfirmAction.SURRENDER:
        game.surrender()
        return True
    return False  # ConfirmAction.EXIT


def _handle_confirm_event(event: pygame.event.Event, game: Game, ui_state: UIState) -> bool:
    action = ui_state.pending_confirmation
    if event.type == pygame.KEYDOWN:
        if event.key in (pygame.K_RETURN, pygame.K_y):
            ui_state.pending_confirmation = None
            return _resolve_confirmation(action, game, ui_state)
        if event.key == pygame.K_ESCAPE:
            ui_state.pending_confirmation = None
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = _design_pos(event.pos)
        if layout.CONFIRM_YES_BUTTON_RECT.collidepoint(pos):
            ui_state.pending_confirmation = None
            return _resolve_confirmation(action, game, ui_state)
        if layout.CONFIRM_NO_BUTTON_RECT.collidepoint(pos):
            ui_state.pending_confirmation = None
    return True


def _handle_mousewheel(event: pygame.event.Event, game: Game, ui_state: UIState) -> None:
    if not layout.PANEL_HISTORY_REGION_RECT.collidepoint(_design_pos(pygame.mouse.get_pos())):
        return
    max_offset = max(0, len(game.history) - layout.PANEL_HISTORY_MAX_ROWS)
    ui_state.history_scroll = max(0, min(ui_state.history_scroll + event.y, max_offset))


def handle_event(
    event: pygame.event.Event,
    game: Game,
    ui_state: UIState,
    series: Series | None = None,
    tournament: Bracket | None = None,
) -> bool:
    if ui_state.pending_confirmation is not None:
        return _handle_confirm_event(event, game, ui_state)
    if event.type == pygame.QUIT:
        return _request_quit(game, ui_state)
    if event.type == pygame.KEYDOWN:
        if not _handle_keydown(event, game, ui_state, series, tournament):
            return False
    if event.type == pygame.MOUSEWHEEL:
        _handle_mousewheel(event, game, ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            if not _handle_left_click(_design_pos(event.pos), game, ui_state, series, tournament):
                return False
        elif event.button == 3 and game.state == TurnState.CHOOSING_PLACEMENT and not is_bots_turn(
            game, ui_state
        ):
            _rotate(ui_state)
    return True
