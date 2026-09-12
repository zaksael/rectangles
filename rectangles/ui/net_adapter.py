"""Drop-in proxy for `Game`, used by ui/input.py to talk to the server over
the wire instead of calling a local Game object in-process. Method
signatures mirror Game's exactly so ui/input.py's call sites don't change,
only which object they call.

A background thread owns an asyncio event loop and the websocket
connection; every received `state` message repopulates this adapter's own
public attributes (mirroring Game's real fields) since ui/renderer.py reads
those attributes directly, not through methods."""

from __future__ import annotations

import asyncio
import json
import queue
import threading

import websockets

from rectangles.board import Board
from rectangles.constants import CellKind
from rectangles.game import GameOverReason
from rectangles.models import Cell, Player, SpecialCell
from server import schema

_TURN_STATE_FROM_WIRE = {v: k for k, v in schema._TURN_STATE_NAMES.items()}
_GAME_OVER_REASON_FROM_WIRE = {v: k for k, v in schema._GAME_OVER_REASON_NAMES.items()}

_REQUEST_TIMEOUT = 10.0
_CONNECT_TIMEOUT = 10.0


def _board_from_wire(data: dict) -> Board:
    house_rules = data["houseRules"]
    special_cells = frozenset(
        SpecialCell(kind, Cell(*cell), pair_id=i)
        for kind in (CellKind.PRIZE, CellKind.PITFALL, CellKind.STEAL)
        for i, cell in enumerate(house_rules[kind.value]["cells"])
    )
    wall_edges = frozenset(
        frozenset(Cell(*cell) for cell in edge) for edge in house_rules["walls"]["edges"]
    )
    obstacle_cells = frozenset(Cell(*cell) for cell in house_rules["obstacles"]["cells"])
    return Board(
        size=data["board"]["size"],
        special_cells=special_cells,
        wall_edges=wall_edges,
        obstacle_cells=obstacle_cells,
    )


def _player_from_wire(player_id: int, board: Board, data: dict) -> Player:
    player = Player(
        id=player_id,
        name=data["name"],
        start_corner=tuple(data["board"]["startCorner"]),
    )
    player.consecutive_skips = data["board"]["consecutiveSkips"]
    player.special_captures = {
        kind: data["houseRules"][kind.value]["captured"] for kind in CellKind
    }
    player.rerolls_used = data["houseRules"]["reroll"]["used"]
    player.comeback_nudge_granted = data["houseRules"]["comebackNudge"]["granted"]
    for piece in data["board"]["pieces"]:
        board.place(player, tuple(piece["topLeft"]), piece["width"], piece["height"])
    return player


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

        self._ws = None
        self._pending_reply: queue.Queue | None = None
        self._connected = threading.Event()
        self._connect_error: BaseException | None = None

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=False)
        self._thread.start()
        connected = self._connected.wait(timeout=_CONNECT_TIMEOUT)
        if self._connect_error is not None:
            raise self._connect_error
        if not connected:
            raise TimeoutError(f"timed out connecting to {url}")

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.create_task(self._connect_and_listen())
        self._loop.run_forever()

    async def _connect_and_listen(self) -> None:
        try:
            async with websockets.connect(self.url) as ws:
                self._ws = ws
                async for raw in ws:
                    self._handle_message(json.loads(raw))
                    self._connected.set()
        except Exception as exc:
            self._connect_error = exc
            self._connected.set()
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _handle_message(self, data: dict) -> None:
        # ponytail: the received Board/players objects are built fresh and
        # swapped in as whole attributes rather than mutated in place, so a
        # concurrent read from the render thread never sees a half-updated
        # object even without a lock. Add a lock if that stops being true.
        if data["type"] == "state":
            self._apply_state(data["game"])
        pending = self._pending_reply
        if pending is not None and pending.empty():
            pending.put(data)

    def _apply_state(self, data: dict) -> None:
        board = _board_from_wire(data)
        self.players = {
            int(player_id): _player_from_wire(int(player_id), board, player_data)
            for player_id, player_data in data["players"].items()
        }
        self.board = board

        self.current_player_id = data["turn"]["currentPlayerId"]
        self.state = _TURN_STATE_FROM_WIRE[data["turn"]["turnState"]]
        self.last_roll = tuple(data["turn"]["lastRoll"]) if data["turn"]["lastRoll"] is not None else None
        self.legal_cache = {
            (entry["width"], entry["height"]): {tuple(c) for c in entry["topLefts"]}
            for entry in data["turn"]["legalPlacements"]
        }
        self.wildcard_index = None
        self.wildcard_original_roll = None

        reason = _GAME_OVER_REASON_FROM_WIRE.get(data["gameOver"]["reason"])
        player_id = data["gameOver"]["playerId"]
        self.game_over_reason = reason
        self.skipped_out_player_id = player_id if reason is GameOverReason.SKIP_LIMIT else None
        self.blocked_player_id = player_id if reason is GameOverReason.PLAYER_BLOCKED else None
        self.surrendered_player_id = player_id if reason is GameOverReason.SURRENDER else None

        self.history = []

    def _request(self, msg) -> dict:
        reply_queue: queue.Queue = queue.Queue(maxsize=1)
        self._pending_reply = reply_queue
        try:
            asyncio.run_coroutine_threadsafe(
                self._ws.send(json.dumps(msg.to_json())), self._loop
            ).result()
            return reply_queue.get(timeout=_REQUEST_TIMEOUT)
        finally:
            self._pending_reply = None

    def _raise_if_error(self, reply: dict) -> None:
        if reply["type"] == "error":
            raise ValueError(reply["message"])

    def roll_dice(self) -> tuple[int, int]:
        reply = self._request(schema.RollMsg(protocol_version=1))
        self._raise_if_error(reply)
        return self.last_roll

    def attempt_place(self, top_left: tuple[int, int], w: int, h: int) -> bool:
        reply = self._request(schema.PlaceMsg(protocol_version=1, top_left=top_left, width=w, height=h))
        if reply["type"] == "error" and reply["reason"] == schema.ErrorReason.ILLEGAL_PLACEMENT.value:
            return False
        self._raise_if_error(reply)
        return True

    def confirm_skip(self) -> None:
        reply = self._request(schema.SkipMsg(protocol_version=1))
        self._raise_if_error(reply)

    def surrender(self) -> None:
        # Game.surrender() never errors (see server/app.py's ActionError
        # mapping); no error check needed here.
        self._request(schema.SurrenderMsg(protocol_version=1))

    def end_turn(self) -> None:
        # The server folds end_turn() into its place/skip handling
        # internally - this stays a permanent local no-op purely so
        # ui/input_common.py's call sites don't need to change.
        pass

    def check_game_over(self) -> bool:
        # Same reasoning as end_turn(): the server already folds this into
        # its place/skip handling and broadcasts the result.
        return False

    def can_reroll(self) -> bool:
        # Reroll/chooseWildcard aren't proxied through this adapter at
        # all - a deliberate scope limit, not an unfinished wiring gap -
        # so a server-backed game's real answer is always False here.
        return False

    def close(self) -> None:
        if not self._thread.is_alive():
            return
        if self._ws is not None:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop).result()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)
