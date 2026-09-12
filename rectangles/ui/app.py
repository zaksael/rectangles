from __future__ import annotations

import os

import pygame

from .. import persistence
from ..constants import PLAYER_2, REPLAY_SPEED_MS
from ..game import Game, TurnState
from ..series import Series
from ..tournament import Bracket
from . import input as game_input
from . import layout
from .net_adapter import ServerGameAdapter
from .renderer import Renderer
from .state import Screen, UIState

FPS = 60
AUTO_ACTION_DELAY_MS = 500

# Without this, macOS Retina gives a 2x backing store while mouse events stay
# in 1x coords, shrinking every button's clickable area. Must precede pygame.init().
os.environ.setdefault("SDL_VIDEO_HIGHDPI_DISABLED", "1")

# Opt-in only - today's offline single-player experience stays the
# default. When set, Single-mode games play over the WebSocket protocol
# against an auto-started local server instead of an in-process Game, to
# prove the client/server boundary.
_USE_SERVER = os.environ.get("RECTANGLES_USE_SERVER") == "1"


def _new_game(ui_state: UIState, server_url: str | None) -> Game | ServerGameAdapter:
    if server_url is not None:
        query = (
            f"?protocolVersion=1&boardSize={ui_state.selected_board_size}"
            f"&skipLimit={ui_state.selected_skip_limit}"
        )
        if ui_state.selected_bot_enabled:
            query += f"&botSeats={PLAYER_2}&botDifficulty={ui_state.selected_bot_difficulty}"
        return ServerGameAdapter(f"{server_url}{query}")
    return Game(
        board_size=ui_state.selected_board_size,
        skip_limit=ui_state.selected_skip_limit,
        prize_enabled=ui_state.selected_prize_enabled,
        walls_enabled=ui_state.selected_walls_enabled,
        obstacles_enabled=ui_state.selected_obstacles_enabled,
        pitfall_enabled=ui_state.selected_pitfall_enabled,
        steal_enabled=ui_state.selected_steal_enabled,
        wildcard_enabled=ui_state.selected_wildcard_enabled,
        self_enclosed_penalty_enabled=ui_state.selected_self_enclosed_penalty_enabled,
        reroll_enabled=ui_state.selected_reroll_enabled,
        comeback_nudge_enabled=ui_state.selected_comeback_nudge_enabled,
    )


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Rectangles")
    screen = pygame.display.set_mode((layout.DESIGN_WIDTH, layout.DESIGN_HEIGHT), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    game: Game | ServerGameAdapter | None = None
    series: Series | None = None
    tournament: Bracket | None = None
    series_game_recorded = False
    game_is_series_round = True  # False while `game` is a match's standalone tiebreak Game
    auto_action_at: int | None = None
    replay_autoplay_at: int | None = None
    ui_state = UIState()
    renderer = Renderer(screen)

    server_url: str | None = None
    if _USE_SERVER:
        from server.app import run_in_background

        server_url, _ = run_in_background()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                # The UI is scaled to fit any window size, so just clamp to a usability floor.
                width = max(event.w, layout.MIN_REAL_WINDOW_WIDTH)
                height = max(event.h, layout.MIN_REAL_WINDOW_HEIGHT)
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                renderer.resize(screen)
                continue
            if ui_state.screen == Screen.MODE_SELECT:
                if not game_input.handle_mode_select_event(event, ui_state):
                    running = False
            elif ui_state.screen == Screen.SETTINGS:
                if not game_input.handle_settings_event(event, ui_state):
                    running = False
            elif ui_state.screen == Screen.REPLAY:
                if not game_input.handle_replay_event(event, ui_state, game):
                    running = False
            elif ui_state.screen == Screen.TOURNAMENT:
                if not game_input.handle_tournament_event(event, ui_state, tournament):
                    running = False
            else:
                if not game_input.handle_event(event, game, ui_state, series, tournament):
                    running = False

        if isinstance(game, ServerGameAdapter) and (
            ui_state.game_requested
            or ui_state.series_requested
            or ui_state.tournament_requested
            or ui_state.resume_requested
        ):
            game.close()

        if ui_state.game_requested:
            game = _new_game(ui_state, server_url)
            series = None
            tournament = None
            ui_state.active_bot_seats = (
                {} if isinstance(game, ServerGameAdapter) else game_input.plain_bot_seats(ui_state)
            )
            series_game_recorded = False
            game_is_series_round = True
            auto_action_at = None
            ui_state.game_requested = False

        if ui_state.series_requested:
            series = Series(
                length=ui_state.selected_series_length,
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
                prize_enabled=ui_state.selected_prize_enabled,
                walls_enabled=ui_state.selected_walls_enabled,
                obstacles_enabled=ui_state.selected_obstacles_enabled,
                pitfall_enabled=ui_state.selected_pitfall_enabled,
                steal_enabled=ui_state.selected_steal_enabled,
                wildcard_enabled=ui_state.selected_wildcard_enabled,
                self_enclosed_penalty_enabled=ui_state.selected_self_enclosed_penalty_enabled,
                reroll_enabled=ui_state.selected_reroll_enabled,
                comeback_nudge_enabled=ui_state.selected_comeback_nudge_enabled,
            )
            game = series.new_game()
            tournament = None
            ui_state.active_bot_seats = game_input.plain_bot_seats(ui_state)
            series_game_recorded = False
            game_is_series_round = True
            auto_action_at = None
            ui_state.series_requested = False

        if ui_state.tournament_requested:
            participants = game_input.build_tournament_participants(ui_state)
            tournament = Bracket(
                participants=participants,
                series_length=ui_state.selected_series_length,
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
                prize_enabled=ui_state.selected_prize_enabled,
                walls_enabled=ui_state.selected_walls_enabled,
                obstacles_enabled=ui_state.selected_obstacles_enabled,
                pitfall_enabled=ui_state.selected_pitfall_enabled,
                steal_enabled=ui_state.selected_steal_enabled,
                wildcard_enabled=ui_state.selected_wildcard_enabled,
                self_enclosed_penalty_enabled=ui_state.selected_self_enclosed_penalty_enabled,
                reroll_enabled=ui_state.selected_reroll_enabled,
                comeback_nudge_enabled=ui_state.selected_comeback_nudge_enabled,
            )
            game = None
            series = None
            series_game_recorded = False
            auto_action_at = None
            ui_state.tournament_requested = False

        if ui_state.begin_match_requested:
            match = tournament.current_match()
            series = tournament.new_series_for_current_match()
            game = game_input.start_tournament_match_game(tournament, match, ui_state)
            game_is_series_round = True
            ui_state.screen = Screen.PLAYING
            series_game_recorded = False
            auto_action_at = None
            ui_state.begin_match_requested = False

        if ui_state.resume_requested:
            loaded = persistence.load_all()
            if loaded is None:
                ui_state.screen = Screen.MODE_SELECT
                tournament = None
                ui_state.active_bot_seats = game_input.plain_bot_seats(ui_state)
            else:
                game, series, tournament = loaded
                if tournament is not None:
                    match = tournament.current_match()
                    if match.tiebreak_game is not None:
                        game = match.tiebreak_game
                        series = match.series
                        game_is_series_round = False
                    else:
                        match.series = series
                        game_is_series_round = True
                    game_input.apply_match_identity(game, tournament, match, ui_state)
                else:
                    game_is_series_round = True
                    ui_state.active_bot_seats = game_input.plain_bot_seats(ui_state)
            series_game_recorded = False
            auto_action_at = None
            ui_state.resume_requested = False

        if ui_state.next_game_requested:
            game = series.new_game()
            if tournament is not None:
                game_input.apply_match_identity(game, tournament, tournament.current_match(), ui_state)
            game_is_series_round = True
            series_game_recorded = False
            auto_action_at = None
            ui_state.next_game_requested = False

        if ui_state.next_match_requested:
            match = tournament.current_match()
            if match.series.winner() is None and match.tiebreak_game is None:
                match.tiebreak_game = tournament.new_tiebreak_game()
                game = match.tiebreak_game
                game_input.apply_match_identity(game, tournament, match, ui_state)
                game_is_series_round = False
            else:
                tournament.record_match_result()
                tournament.advance()
                if tournament.is_complete():
                    ui_state.screen = Screen.TOURNAMENT
                else:
                    match = tournament.current_match()
                    series = tournament.new_series_for_current_match()
                    game = game_input.start_tournament_match_game(tournament, match, ui_state)
                    game_is_series_round = True
            series_game_recorded = False
            auto_action_at = None
            ui_state.next_match_requested = False

        if (
            series is not None
            and game is not None
            and game_is_series_round
            and game.state == TurnState.GAME_OVER
            and not series_game_recorded
        ):
            series.record_game(game)
            series_game_recorded = True

        should_auto_act = (
            ui_state.screen == Screen.PLAYING
            and game is not None
            and game.state != TurnState.GAME_OVER
            and ui_state.pending_confirmation is None
            and (
                game_input.is_bots_turn(game, ui_state)
                # With a reroll charge available, SKIPPED is a real Reroll-vs-Skip
                # decision and must wait for the player.
                or (game.state == TurnState.SKIPPED and not game.can_reroll())
            )
        )
        if not should_auto_act:
            auto_action_at = None
        elif auto_action_at is None:
            # Arm, don't fire: the triggering state may have become true this
            # frame, and firing now would skip it before draw() ever shows it.
            auto_action_at = pygame.time.get_ticks() + AUTO_ACTION_DELAY_MS
        elif pygame.time.get_ticks() >= auto_action_at:
            if game_input.is_bots_turn(game, ui_state):
                game_input.take_bot_turn(game, ui_state)
            else:
                game_input.continue_turn(game)
            auto_action_at = None

        should_autoplay = (
            ui_state.screen == Screen.REPLAY
            and ui_state.replay_autoplay
            and game is not None
            and ui_state.replay_step < len(game.history)
        )
        if not should_autoplay:
            replay_autoplay_at = None
        elif replay_autoplay_at is None:
            # Arm-then-fire, as with auto_action_at above.
            replay_autoplay_at = pygame.time.get_ticks() + REPLAY_SPEED_MS[ui_state.replay_speed]
        elif pygame.time.get_ticks() >= replay_autoplay_at:
            ui_state.replay_step += 1
            if ui_state.replay_step >= len(game.history):
                ui_state.replay_autoplay = False
            replay_autoplay_at = None

        if ui_state.screen == Screen.PLAYING and not game_input.is_bots_turn(game, ui_state):
            game_input.update_hover(game, ui_state)

        renderer.draw(game, ui_state, series, tournament)
        clock.tick(FPS)

    if isinstance(game, ServerGameAdapter):
        # A server-backed game can't be serialized by persistence.py (it
        # reads Game-only fields the adapter never populates) - and per
        # ROADMAP.md, save/load for networked games isn't this milestone's
        # concern anyway.
        game.close()
    elif persistence.should_save_on_exit(game, series, tournament):
        persistence.save_game(game, series, tournament)

    pygame.quit()
