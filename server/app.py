import json
import os
import re
import threading
import time
from typing import Callable

import uvicorn
from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from rectangles.constants import (
    BOARD_SIZE,
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    PLAYER_2,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT,
    SKIP_LIMIT_PRESETS,
)
from rectangles import bot
from rectangles.game import Game, TurnState
from server.schema import ChooseWildcardMsg, ErrorMsg, ErrorReason, PlaceMsg, StateMsg, serialize_game

HOST = os.environ.get("RECTANGLES_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RECTANGLES_SERVER_PORT", "8765"))

PROTOCOL_VERSION = 1

_PRESET_PARAMS = {
    "protocolVersion": (PROTOCOL_VERSION,),
    "boardSize": BOARD_SIZE_PRESETS,
    "skipLimit": SKIP_LIMIT_PRESETS,
    "seriesLength": SERIES_LENGTH_PRESETS,
    "botSeats": (PLAYER_2,),
    "botDifficulty": BOT_DIFFICULTY_PRESETS,
}

_BOOL_PARAM_NAMES = {
    "wildcardEnabled",
    "rerollEnabled",
    "wallsEnabled",
    "obstaclesEnabled",
    "prizeEnabled",
    "pitfallEnabled",
    "stealEnabled",
    "selfEnclosedPenaltyEnabled",
}

_INT_PARAM_NAMES = {"prizePoints", "pitfallPoints", "stealPoints"}

app = FastAPI()


def _connect_params_valid(query_params) -> bool:
    if "protocolVersion" not in query_params:
        return False
    if not set(query_params.keys()) <= _PRESET_PARAMS.keys() | _BOOL_PARAM_NAMES | _INT_PARAM_NAMES:
        return False
    for name, presets in _PRESET_PARAMS.items():
        value = query_params.get(name)
        if value is None:
            continue
        cast = type(presets[0])
        try:
            if cast(value) not in presets:
                return False
        except ValueError:
            return False
    for name in _BOOL_PARAM_NAMES:
        value = query_params.get(name)
        if value is not None and value not in ("true", "false"):
            return False
    for name in _INT_PARAM_NAMES:
        value = query_params.get(name)
        if value is None:
            continue
        try:
            if int(value) < 0:
                return False
        except ValueError:
            return False
    return True


async def _send_error(websocket: WebSocket, reason: ErrorReason, message: str) -> None:
    error = ErrorMsg(protocol_version=PROTOCOL_VERSION, reason=reason, message=message)
    await websocket.send_json(error.to_json())


async def _broadcast_state(websocket: WebSocket, game: Game) -> None:
    state = StateMsg(protocol_version=PROTOCOL_VERSION, game=serialize_game(game))
    await websocket.send_json(state.to_json())


def _bool_param_to_kwarg(name: str) -> str:
    base = name[: -len("Enabled")]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower() + "_enabled"


def _game_from_connect_params(query_params) -> Game:
    board_size = int(query_params.get("boardSize", BOARD_SIZE))
    skip_limit = int(query_params.get("skipLimit", SKIP_LIMIT))
    bool_kwargs = {
        _bool_param_to_kwarg(name): query_params.get(name) == "true" for name in _BOOL_PARAM_NAMES
    }
    special_cell_points = {}
    if "prizePoints" in query_params:
        special_cell_points["prize"] = int(query_params["prizePoints"])
    if "pitfallPoints" in query_params:
        special_cell_points["pitfall"] = int(query_params["pitfallPoints"])
    if "stealPoints" in query_params:
        special_cell_points["steal"] = int(query_params["stealPoints"])
    return Game(
        board_size=board_size,
        skip_limit=skip_limit,
        special_cell_points=special_cell_points,
        **bool_kwargs,
    )


def _bot_difficulty_from_connect_params(query_params) -> str | None:
    if "botSeats" not in query_params:
        return None
    return query_params.get("botDifficulty", "Basic")


class ActionError(Exception):
    def __init__(self, reason: ErrorReason, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def _advance_turn(game: Game) -> None:
    if not game.check_game_over():
        game.end_turn()


def _apply_action(game: Game, data: dict) -> None:
    action_type = data["type"]
    if action_type == "roll":
        try:
            game.roll_dice()
        except ValueError as exc:
            raise ActionError(ErrorReason.INVALID_ACTION, str(exc)) from exc
    elif action_type == "place":
        try:
            place = PlaceMsg.from_json(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise ActionError(ErrorReason.MALFORMED_MESSAGE, "malformed place message") from exc
        if not game.attempt_place(place.top_left, place.width, place.height):
            raise ActionError(ErrorReason.ILLEGAL_PLACEMENT, "illegal placement")
        _advance_turn(game)
    elif action_type == "skip":
        try:
            game.confirm_skip()
        except ValueError as exc:
            raise ActionError(ErrorReason.INVALID_ACTION, str(exc)) from exc
        _advance_turn(game)
    elif action_type == "chooseWildcard":
        try:
            wildcard = ChooseWildcardMsg.from_json(data)
        except (KeyError, TypeError) as exc:
            raise ActionError(ErrorReason.MALFORMED_MESSAGE, "malformed chooseWildcard message") from exc
        if game.state != TurnState.CHOOSING_WILDCARD:
            raise ActionError(ErrorReason.INVALID_ACTION, f"Cannot choose a wildcard value in state {game.state}")
        try:
            game.choose_wildcard_value(wildcard.value)
        except ValueError as exc:
            raise ActionError(ErrorReason.ILLEGAL_WILDCARD_VALUE, str(exc)) from exc
    elif action_type == "reroll":
        try:
            game.reroll()
        except ValueError as exc:
            raise ActionError(ErrorReason.INVALID_ACTION, str(exc)) from exc
    elif action_type == "surrender":
        game.surrender()
    else:
        raise ActionError(ErrorReason.MALFORMED_MESSAGE, "unknown action type")


def _bot_turn_step(game: Game, difficulty: str) -> bool:
    """Performs one atomic bot action. Returns False for a turn state this
    step doesn't (yet) handle, so the caller's loop can stop instead of
    spinning forever re-broadcasting an unchanged state."""
    if bot.should_reroll(game, difficulty):
        game.reroll()
    elif game.state == TurnState.AWAITING_ROLL:
        game.roll_dice()
    elif game.state == TurnState.CHOOSING_WILDCARD:
        game.choose_wildcard_value(bot.choose_wildcard_value(game, difficulty))
    elif game.state == TurnState.CHOOSING_PLACEMENT:
        top_left, w, h = bot.choose_placement(game, difficulty)
        game.attempt_place(top_left, w, h)
        _advance_turn(game)
    elif game.state == TurnState.SKIPPED:
        game.confirm_skip()
        _advance_turn(game)
    else:
        return False
    return True


async def _broadcast_and_run_bots(websocket: WebSocket, game: Game, bot_difficulty: str | None) -> None:
    await _broadcast_state(websocket, game)
    while (
        bot_difficulty is not None
        and game.state != TurnState.GAME_OVER
        and game.current_player_id == PLAYER_2
    ):
        if not _bot_turn_step(game, bot_difficulty):
            break
        await _broadcast_state(websocket, game)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    if not _connect_params_valid(websocket.query_params):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    game = _game_from_connect_params(websocket.query_params)
    bot_difficulty = _bot_difficulty_from_connect_params(websocket.query_params)
    await _broadcast_and_run_bots(websocket, game, bot_difficulty)
    try:
        while True:
            text = await websocket.receive_text()
            try:
                data = json.loads(text)
                if not isinstance(data, dict) or "type" not in data:
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                await _send_error(websocket, ErrorReason.MALFORMED_MESSAGE, "malformed message")
                continue
            if data.get("protocolVersion") != PROTOCOL_VERSION:
                await _send_error(
                    websocket, ErrorReason.PROTOCOL_VERSION_MISMATCH, "protocol version mismatch"
                )
                continue
            try:
                _apply_action(game, data)
            except ActionError as exc:
                await _send_error(websocket, exc.reason, exc.message)
                continue
            await _broadcast_and_run_bots(websocket, game, bot_difficulty)
    except WebSocketDisconnect:
        pass


def run_in_background(host: str = "127.0.0.1", port: int = 0) -> tuple[str, Callable[[], None]]:
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    actual_port = server.servers[0].sockets[0].getsockname()[1]

    def stop() -> None:
        server.should_exit = True
        thread.join(timeout=5)

    return f"ws://{host}:{actual_port}/ws", stop


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
