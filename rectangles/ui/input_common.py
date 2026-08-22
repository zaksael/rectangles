from __future__ import annotations

import pygame

from .. import bot
from ..constants import DICE_MAX, DICE_MIN, PLAYER_1, PLAYER_2
from ..game import Game, TurnState
from ..series import Series
from ..tournament import Bracket, Match, Participant
from . import layout
from .state import Screen, UIState


def _current_window_size() -> tuple[int, int]:
    # The real window can be resized (see ui/app.py's VIDEORESIZE handling) and
    # freely scaled relative to the fixed design canvas (see layout.compute_scale),
    # so translating a real mouse/click position needs the live real size, not
    # a static default. Falls back to the design size when no display exists
    # yet (e.g. headless tests) - equivalent to an unscaled 1:1 canvas.
    surface = pygame.display.get_surface()
    return surface.get_size() if surface is not None else (layout.DESIGN_WIDTH, layout.DESIGN_HEIGHT)


def _design_pos(pos: tuple[int, int]) -> tuple[int, int]:
    # Every layout rect is defined in the fixed design canvas' coordinate
    # space; a real mouse/click position must be mapped back into that space
    # before any hit-testing - the one place this happens, mirroring
    # Renderer._mouse_pos on the drawing side.
    return layout.to_design_coords(*pos, *_current_window_size())


def compute_top_left(game: Game, w: int, h: int, cell: tuple[int, int]) -> tuple[int, int]:
    r, c = cell
    r -= h // 2
    c -= w // 2
    r = max(0, min(r, game.board.size - h))
    c = max(0, min(c, game.board.size - w))
    return (r, c)


def _rotate(ui_state: UIState) -> None:
    if ui_state.current_dims is None:
        return
    w, h = ui_state.current_dims
    ui_state.current_dims = (h, w)


def _new_game(ui_state: UIState) -> None:
    ui_state.reset()
    ui_state.screen = Screen.MODE_SELECT


def _roll_dice(game: Game, ui_state: UIState) -> None:
    a, b = game.roll_dice()
    if game.state == TurnState.CHOOSING_PLACEMENT:
        ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)


def _choose_wildcard_value(game: Game, ui_state: UIState, value: int) -> None:
    game.choose_wildcard_value(value)
    if game.state == TurnState.CHOOSING_PLACEMENT:
        a, b = game.last_roll
        ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)


def _reroll(game: Game, ui_state: UIState) -> None:
    game.reroll()
    if game.state == TurnState.CHOOSING_PLACEMENT:
        a, b = game.last_roll
        ui_state.current_dims = (a, b) if game.legal_cache.get((a, b)) else (b, a)


def continue_turn(game: Game) -> None:
    game.confirm_skip()
    if not game.check_game_over():
        game.end_turn()


def is_bots_turn(game: Game, ui_state: UIState) -> bool:
    return game.current_player_id in ui_state.active_bot_seats


def plain_bot_seats(ui_state: UIState) -> dict[int, str]:
    # For a plain (non-tournament) Start Game/Series/Resume - the bot, if
    # on, is always seated PLAYER_2, per the settings-screen toggle.
    return {PLAYER_2: ui_state.selected_bot_difficulty} if ui_state.selected_bot_enabled else {}


def take_bot_turn(game: Game, ui_state: UIState) -> None:
    if game.state == TurnState.AWAITING_ROLL:
        _roll_dice(game, ui_state)
    elif game.state == TurnState.CHOOSING_WILDCARD:
        # Bot always picks uniformly at random, independent of difficulty -
        # Greedy/Blocking only affect placement choice, not this.
        _choose_wildcard_value(game, ui_state, game.rng.randint(DICE_MIN, DICE_MAX))
    elif game.state == TurnState.SKIPPED:
        continue_turn(game)
    elif game.state == TurnState.CHOOSING_PLACEMENT:
        difficulty = ui_state.active_bot_seats[game.current_player_id]
        top_left, w, h = bot.choose_placement(game, difficulty)
        if game.attempt_place(top_left, w, h):
            if not game.check_game_over():
                game.end_turn()
            ui_state.reset()


def build_tournament_participants(ui_state: UIState) -> list[Participant]:
    participants: list[Participant] = []
    human_n = 0
    bot_n = 0
    for i in range(ui_state.tournament_size):
        if ui_state.tournament_slot_is_bot[i]:
            bot_n += 1
            difficulty = ui_state.tournament_slot_difficulty[i]
            participants.append(Participant(name=f"Bot {bot_n} ({difficulty})", is_bot=True, bot_difficulty=difficulty))
        else:
            human_n += 1
            participants.append(Participant(name=f"Player {human_n}"))
    return participants


def apply_match_identity(game: Game, tournament: Bracket, match: Match, ui_state: UIState) -> None:
    # Post-construction override, same pattern Series.new_game() already uses
    # for current_player_id and persistence.py's load path already uses for
    # player.name - a fresh Game()/Series.new_game() always resets both to
    # generic defaults, so this must be re-applied every round of a match,
    # not just once at match start.
    p_a = tournament.participants[match.participant_a]
    p_b = tournament.participants[match.participant_b]
    game.players[PLAYER_1].name = p_a.name
    game.players[PLAYER_2].name = p_b.name
    ui_state.active_bot_seats = {}
    if p_a.is_bot:
        ui_state.active_bot_seats[PLAYER_1] = p_a.bot_difficulty
    if p_b.is_bot:
        ui_state.active_bot_seats[PLAYER_2] = p_b.bot_difficulty


def start_tournament_match_game(tournament: Bracket, match: Match, ui_state: UIState) -> Game:
    game = match.series.new_game()
    apply_match_identity(game, tournament, match, ui_state)
    return game


def update_hover(game: Game, ui_state: UIState) -> None:
    if game.state != TurnState.CHOOSING_PLACEMENT or ui_state.current_dims is None:
        ui_state.hover_top_left = None
        return
    cell = layout.pixel_to_cell(*_design_pos(pygame.mouse.get_pos()), game.board.size)
    if cell is None:
        ui_state.hover_top_left = None
        return
    w, h = ui_state.current_dims
    top_left = compute_top_left(game, w, h, cell)
    ui_state.hover_top_left = top_left
    ui_state.hover_legal = top_left in game.legal_cache.get((w, h), set())


def _advance_or_end_series(tournament: Bracket | None, series: Series | None, ui_state: UIState) -> None:
    if series is not None and not series.is_complete():
        ui_state.next_game_requested = True
    elif tournament is not None:
        ui_state.next_match_requested = True
    else:
        _new_game(ui_state)

