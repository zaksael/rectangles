from __future__ import annotations

import pygame

from .. import persistence
from ..constants import PLAYER_1, PLAYER_2
from ..game import Game, TurnState
from ..series import Series
from . import input as game_input
from . import layout
from .renderer import Renderer
from .state import Screen, UIState

FPS = 60
BOT_MOVE_DELAY_MS = 500


def run() -> None:
    pygame.init()
    pygame.display.set_caption("Rectangles")
    screen = pygame.display.set_mode((layout.WINDOW_WIDTH, layout.WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    game: Game | None = None
    series: Series | None = None
    series_game_recorded = False
    bot_next_action_at = 0
    ui_state = UIState()
    renderer = Renderer(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if ui_state.screen == Screen.SETTINGS:
                if not game_input.handle_settings_event(event, ui_state):
                    running = False
            else:
                if not game_input.handle_event(event, game, ui_state, series):
                    running = False

        if ui_state.game_requested:
            game = Game(
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
                doubles_enabled=ui_state.selected_doubles_enabled,
                flag_conquest_enabled=ui_state.selected_flag_conquest_enabled,
                flag_bonus_points=ui_state.selected_flag_bonus_points,
            )
            series = None
            series_game_recorded = False
            bot_next_action_at = 0
            ui_state.game_requested = False

        if ui_state.series_requested:
            series = Series(
                length=ui_state.selected_series_length,
                board_size=ui_state.selected_board_size,
                skip_limit=ui_state.selected_skip_limit,
                doubles_enabled=ui_state.selected_doubles_enabled,
                flag_conquest_enabled=ui_state.selected_flag_conquest_enabled,
                flag_bonus_points=ui_state.selected_flag_bonus_points,
            )
            game = series.new_game()
            series_game_recorded = False
            bot_next_action_at = 0
            ui_state.series_requested = False

        if ui_state.resume_requested:
            loaded = persistence.load_game()
            if loaded is None:
                ui_state.screen = Screen.SETTINGS
            else:
                game, series = loaded
            series_game_recorded = False
            bot_next_action_at = 0
            ui_state.resume_requested = False

        if ui_state.next_game_requested:
            game = series.new_game()
            series_game_recorded = False
            bot_next_action_at = 0
            ui_state.next_game_requested = False

        if series is not None and game is not None and game.state == TurnState.GAME_OVER and not series_game_recorded:
            p1, p2 = game.players[PLAYER_1], game.players[PLAYER_2]
            series.record_game(game.total_score(p1), game.total_score(p2))
            series_game_recorded = True

        if (
            ui_state.screen == Screen.PLAYING
            and game is not None
            and game.state != TurnState.GAME_OVER
            and ui_state.pending_confirmation is None
            and game_input.is_bots_turn(game, ui_state)
            and pygame.time.get_ticks() >= bot_next_action_at
        ):
            game_input.take_bot_turn(game, ui_state)
            bot_next_action_at = pygame.time.get_ticks() + BOT_MOVE_DELAY_MS

        if ui_state.screen == Screen.PLAYING and not game_input.is_bots_turn(game, ui_state):
            game_input.update_hover(game, ui_state)

        renderer.draw(game, ui_state, series)
        clock.tick(FPS)

    if persistence.should_save_on_exit(game, series):
        persistence.save_game(game, series)

    pygame.quit()
