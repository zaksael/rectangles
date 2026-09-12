"""Drop-in proxy for `Game`, used by ui/input.py to talk to the M1 server
over the wire instead of calling a local Game object in-process. Method
signatures mirror Game's exactly so ui/input.py's call sites don't change,
only which object they call.

Stub only: no socket yet. Public attributes stay None until the first
`state` broadcast populates them."""

from __future__ import annotations


class ServerGameAdapter:
    def __init__(self, url: str) -> None:
        self.url = url
        self.board = None
        self.players = None
        self.current_player_id = None
        self.state = None
        self.last_roll = None
        self.wildcard_index = None
        self.wildcard_original_roll = None
        self.legal_cache = None
        self.game_over_reason = None
        self.skipped_out_player_id = None
        self.blocked_player_id = None
        self.surrendered_player_id = None
        self.history = None

    def roll_dice(self) -> tuple[int, int]:
        raise NotImplementedError

    def attempt_place(self, top_left: tuple[int, int], w: int, h: int) -> bool:
        raise NotImplementedError

    def confirm_skip(self) -> None:
        raise NotImplementedError

    def surrender(self) -> None:
        raise NotImplementedError

    def end_turn(self) -> None:
        # The server folds end_turn() into its place/skip handling
        # internally - this stays a permanent local no-op purely so
        # ui/input_common.py's call sites don't need to change.
        pass

    def close(self) -> None:
        raise NotImplementedError
