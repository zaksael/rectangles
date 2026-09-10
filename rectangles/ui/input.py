from __future__ import annotations

# Event handling lives in one input_*.py module per screen, with shared
# helpers in input_common.py. This module just re-exports the surface that
# app.py and tests import from `rectangles.ui.input`.
from .input_common import (
    apply_match_identity,
    build_tournament_participants,
    compute_top_left,
    continue_turn,
    is_bots_turn,
    plain_bot_seats,
    start_tournament_match_game,
    take_bot_turn,
    update_hover,
)
from .input_mode_select import handle_mode_select_event
from .input_playing import handle_event
from .input_replay import handle_replay_event
from .input_settings import handle_settings_event
from .input_tournament import handle_tournament_event
