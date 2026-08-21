from __future__ import annotations

import pygame

from .. import bot, persistence
from ..constants import DICE_MAX, DICE_MIN, PLAYER_1, PLAYER_2, REPLAY_SPEED_PRESETS
from ..game import Game, TurnState
from ..series import Series
from ..tournament import Bracket, Match, Participant
from . import layout
from .state import ConfirmAction, Screen, UIState


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
    ui_state.screen = Screen.SETTINGS


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


def _clamp_replay_step(ui_state: UIState, game: Game) -> None:
    ui_state.replay_step = max(0, min(ui_state.replay_step, len(game.history)))


def handle_replay_event(event: pygame.event.Event, ui_state: UIState, game: Game) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        # Any keyboard nav counts as taking manual control - none of these
        # keys are bound to Play/speed (click-only), so this is safe to do
        # unconditionally before the specific key dispatch below.
        ui_state.replay_autoplay = False
        if event.key == pygame.K_ESCAPE:
            ui_state.screen = Screen.PLAYING
        elif event.key in (pygame.K_RIGHT, pygame.K_DOWN):
            ui_state.replay_step += 1
        elif event.key in (pygame.K_LEFT, pygame.K_UP):
            ui_state.replay_step -= 1
        elif event.key == pygame.K_HOME:
            ui_state.replay_step = 0
        elif event.key == pygame.K_END:
            ui_state.replay_step = len(game.history)
        _clamp_replay_step(ui_state, game)
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = _design_pos(event.pos)
        rects = layout.REPLAY_BUTTON_RECTS
        if any(rects[k].collidepoint(pos) for k in ("first", "prev", "next", "last")):
            ui_state.replay_autoplay = False
        if rects["first"].collidepoint(pos):
            ui_state.replay_step = 0
        elif rects["prev"].collidepoint(pos):
            ui_state.replay_step -= 1
        elif rects["next"].collidepoint(pos):
            ui_state.replay_step += 1
        elif rects["last"].collidepoint(pos):
            ui_state.replay_step = len(game.history)
        elif rects["play"].collidepoint(pos):
            ui_state.replay_autoplay = not ui_state.replay_autoplay
        elif rects["back"].collidepoint(pos):
            ui_state.screen = Screen.PLAYING
        elif layout.REPLAY_REVEAL_BUTTON_RECT.collidepoint(pos):
            ui_state.replay_show_better_option = not ui_state.replay_show_better_option
        else:
            for value in REPLAY_SPEED_PRESETS:
                if rects[value].collidepoint(pos):
                    ui_state.replay_speed = value
                    break
        _clamp_replay_step(ui_state, game)
    return True


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
        # Not gated on wildcard_value_is_legal(): individual values can still
        # be illegal (that's what the grayed-out buttons show) even though
        # roll_dice() guarantees at least one of the six is legal whenever
        # this state is reached at all.
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


def _start_game(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.game_requested = True
    persistence.delete_save()


def _start_series(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.series_requested = True
    persistence.delete_save()


def _resume_game(ui_state: UIState) -> None:
    ui_state.screen = Screen.PLAYING
    ui_state.resume_requested = True


def _start_tournament(ui_state: UIState) -> None:
    ui_state.screen = Screen.TOURNAMENT
    ui_state.tournament_requested = True
    persistence.delete_save()


def _handle_settings_left_click(pos: tuple[int, int], ui_state: UIState) -> bool:
    for value, rect in layout.SETTINGS_BOARD_SIZE_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_board_size = value
            return True
    for value, rect in layout.SETTINGS_SKIP_LIMIT_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_skip_limit = value
            return True
    if layout.SETTINGS_FLAG_CONQUEST_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_flag_conquest_enabled = not ui_state.selected_flag_conquest_enabled
        return True
    if layout.SETTINGS_WALLS_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_walls_enabled = not ui_state.selected_walls_enabled
        return True
    if layout.SETTINGS_OBSTACLES_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_obstacles_enabled = not ui_state.selected_obstacles_enabled
        return True
    if layout.SETTINGS_WILDCARD_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_wildcard_enabled = not ui_state.selected_wildcard_enabled
        return True
    if layout.SETTINGS_SELF_ENCLOSED_PENALTY_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_self_enclosed_penalty_enabled = not ui_state.selected_self_enclosed_penalty_enabled
        return True
    if layout.SETTINGS_REROLL_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_reroll_enabled = not ui_state.selected_reroll_enabled
        return True
    if layout.SETTINGS_ALL_RULES_BUTTON_RECT.collidepoint(pos):
        ui_state.toggle_all_house_rules()
        return True
    if layout.SETTINGS_BOT_BUTTON_RECT.collidepoint(pos):
        ui_state.selected_bot_enabled = not ui_state.selected_bot_enabled
        return True
    if ui_state.selected_bot_enabled:
        for value, rect in layout.SETTINGS_BOT_DIFFICULTY_BUTTON_RECTS.items():
            if rect.collidepoint(pos):
                ui_state.selected_bot_difficulty = value
                return True
    for value, rect in layout.SETTINGS_SERIES_LENGTH_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.selected_series_length = value
            return True
    for value, rect in layout.SETTINGS_TOURNAMENT_SIZE_BUTTON_RECTS.items():
        if rect.collidepoint(pos):
            ui_state.tournament_size = value
            return True
    for i in range(ui_state.tournament_size):
        if layout.SETTINGS_TOURNAMENT_SLOT_TOGGLE_RECTS[i].collidepoint(pos):
            ui_state.tournament_slot_is_bot[i] = not ui_state.tournament_slot_is_bot[i]
            return True
        if ui_state.tournament_slot_is_bot[i]:
            for value, rect in layout.SETTINGS_TOURNAMENT_SLOT_DIFFICULTY_RECTS[i].items():
                if rect.collidepoint(pos):
                    ui_state.tournament_slot_difficulty[i] = value
                    return True
    if layout.SETTINGS_START_BUTTON_RECT.collidepoint(pos):
        _start_game(ui_state)
        return True
    if layout.SETTINGS_START_SERIES_BUTTON_RECT.collidepoint(pos):
        _start_series(ui_state)
        return True
    if layout.SETTINGS_START_TOURNAMENT_BUTTON_RECT.collidepoint(pos):
        _start_tournament(ui_state)
        return True
    if persistence.has_save() and layout.SETTINGS_RESUME_BUTTON_RECT.collidepoint(pos):
        _resume_game(ui_state)
        return True
    if layout.SETTINGS_EXIT_BUTTON_RECT.collidepoint(pos):
        return False
    return True


def _handle_settings_mousewheel(event: pygame.event.Event, ui_state: UIState) -> None:
    ui_state.settings_scroll = max(
        0, min(ui_state.settings_scroll - event.y * 40, layout.SETTINGS_MAX_SCROLL)
    )


def handle_settings_event(event: pygame.event.Event, ui_state: UIState) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            return False
        if event.key == pygame.K_SPACE:
            _start_game(ui_state)
        elif event.key == pygame.K_r and persistence.has_save():
            _resume_game(ui_state)
    if event.type == pygame.MOUSEWHEEL:
        _handle_settings_mousewheel(event, ui_state)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # Click positions are in real-window coordinates; map back into the
        # design canvas first, then account for the settings content itself
        # possibly being scrolled up within a taller virtual surface (see
        # Renderer._settings_surface) before hit-testing.
        design_x, design_y = _design_pos(event.pos)
        pos = (design_x, design_y + ui_state.settings_scroll)
        return _handle_settings_left_click(pos, ui_state)
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


def _resolve_confirmation(action: ConfirmAction | None, game: Game, ui_state: UIState) -> bool:
    if action == ConfirmAction.NEW_GAME:
        _new_game(ui_state)
        return True
    if action == ConfirmAction.SURRENDER:
        game.surrender()
        return True
    return False  # ConfirmAction.EXIT


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


def handle_tournament_event(event: pygame.event.Event, ui_state: UIState, tournament: Bracket) -> bool:
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        match = tournament.current_match()
        if not tournament.is_complete() and match is not None and match.series is not None:
            ui_state.screen = Screen.PLAYING
        return True
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        pos = _design_pos(event.pos)
        if layout.TOURNAMENT_ACTION_BUTTON_RECT.collidepoint(pos):
            if tournament.is_complete():
                _new_game(ui_state)
            else:
                match = tournament.current_match()
                if match.series is None:
                    ui_state.begin_match_requested = True
                else:
                    ui_state.screen = Screen.PLAYING
    return True
