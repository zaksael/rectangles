from __future__ import annotations

# Event handling is split into one sibling input_*.py module per screen
# (input_playing/input_settings/input_mode_select/input_replay/input_tournament),
# with the actions/helpers shared across them in input_common.py - same
# split as renderer.py's per-screen mixins, adapted for plain functions
# instead of a class, since there's no shared instance state here to
# justify mixin inheritance. This module just re-exports the public surface
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
