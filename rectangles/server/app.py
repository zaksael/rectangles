import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from starlette.websockets import WebSocketDisconnect

from rectangles.engine.constants import (
    BOARD_SIZE,
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    PLAYER_1,
    PLAYER_2,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT,
    SKIP_LIMIT_PRESETS,
)
from rectangles.engine import bot
from rectangles.engine.analysis import turn_analyses
from rectangles.engine.game import Game, TurnState
from rectangles.engine.series import Series
from .schema import (
    PROTOCOL_VERSION,
    AnalysisMsg,
    ChooseWildcardMsg,
    ErrorMsg,
    ErrorReason,
    PlaceMsg,
    StateMsg,
    serialize_analysis,
    serialize_game,
    serialize_series,
)

HOST = os.environ.get("RECTANGLES_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RECTANGLES_SERVER_PORT", "8765"))
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

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
    "comebackNudgeEnabled",
}

app = FastAPI()


class _HardenedStaticFiles(StaticFiles):
    """StaticFiles that forbids framing the page and sniffing a response's content type."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    """Serve a built frontend (`npm run build`) from `/`, beside `/ws`. A no-op when the folder is missing,
    so development (the Vite proxy) and the tests are unchanged. Mount it after the `/ws` route: a mount at
    `/` matches every path, so anything registered later would never be reached."""
    if dist_dir.is_dir():
        app.mount("/", _HardenedStaticFiles(directory=dist_dir, html=True), name="frontend")


def _connect_params_valid(query_params) -> bool:
    if "protocolVersion" not in query_params:
        return False
    if not set(query_params.keys()) <= _PRESET_PARAMS.keys() | _BOOL_PARAM_NAMES:
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
    return True


async def _send_error(websocket: WebSocket, reason: ErrorReason, message: str) -> None:
    error = ErrorMsg(protocol_version=PROTOCOL_VERSION, reason=reason, message=message)
    await websocket.send_json(error.to_json())


async def _broadcast_state(websocket: WebSocket, game: Game, series: Series | None) -> None:
    state = StateMsg(
        protocol_version=PROTOCOL_VERSION,
        game=serialize_game(game),
        series=serialize_series(series) if series is not None else None,
    )
    await websocket.send_json(state.to_json())


def _bool_param_to_kwarg(name: str) -> str:
    base = name[: -len("Enabled")]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower() + "_enabled"


def _rules_kwargs_from_connect_params(query_params) -> dict:
    bool_kwargs = {
        _bool_param_to_kwarg(name): query_params.get(name) == "true" for name in _BOOL_PARAM_NAMES
    }
    return {
        "board_size": int(query_params.get("boardSize", BOARD_SIZE)),
        "skip_limit": int(query_params.get("skipLimit", SKIP_LIMIT)),
        **bool_kwargs,
    }


def _game_from_connect_params(query_params) -> Game:
    game = Game(**_rules_kwargs_from_connect_params(query_params))
    # Moving first is an advantage: a series alternates the starter, a single game flips a coin.
    game.current_player_id = game.rng.choice((PLAYER_1, PLAYER_2))
    return game


def _series_from_connect_params(query_params) -> Series | None:
    if "seriesLength" not in query_params:
        return None
    return Series(length=int(query_params["seriesLength"]), **_rules_kwargs_from_connect_params(query_params))


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


def _record_round_if_over(series: Series | None, game: Game, recorded: bool) -> bool:
    if series is not None and game.state == TurnState.GAME_OVER and not recorded:
        series.record_game(game)
        return True
    return recorded


async def _broadcast_and_run_bots(
    websocket: WebSocket,
    game: Game,
    series: Series | None,
    bot_difficulty: str | None,
    series_game_recorded: bool = False,
) -> bool:
    series_game_recorded = _record_round_if_over(series, game, series_game_recorded)
    await _broadcast_state(websocket, game, series)
    while (
        bot_difficulty is not None
        and game.state != TurnState.GAME_OVER
        and game.current_player_id == PLAYER_2
    ):
        if not _bot_turn_step(game, bot_difficulty):
            break
        series_game_recorded = _record_round_if_over(series, game, series_game_recorded)
        await _broadcast_state(websocket, game, series)
    return series_game_recorded


def _origin_allowed(headers) -> bool:
    """Browsers always send Origin on a WebSocket upgrade; refuse a page served from anywhere but this host.

    No Origin means a non-browser client (a script, a test), which cross-site hijacking can't use.
    shortcut: same-host only, no allowlist; add one if a proxy that rewrites Host ever fronts the server.
    """
    origin = headers.get("origin")
    return origin is None or urlparse(origin).netloc == headers.get("host")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    if not _origin_allowed(websocket.headers) or not _connect_params_valid(websocket.query_params):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    series = _series_from_connect_params(websocket.query_params)
    game = series.new_game() if series is not None else _game_from_connect_params(websocket.query_params)
    bot_difficulty = _bot_difficulty_from_connect_params(websocket.query_params)
    series_game_recorded = await _broadcast_and_run_bots(websocket, game, series, bot_difficulty)
    analysis_cache: tuple[Game, list[dict]] | None = None  # the game it was computed for (compared with `is`), its wire turns
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
            if data.get("type") == "continueSeries":
                if series is None or series.is_complete() or game.state != TurnState.GAME_OVER:
                    await _send_error(websocket, ErrorReason.INVALID_ACTION, "no series round to continue")
                    continue
                game = series.new_game()
                series_game_recorded = await _broadcast_and_run_bots(websocket, game, series, bot_difficulty)
                continue
            if data.get("type") == "requestAnalysis":
                if game.state != TurnState.GAME_OVER:
                    await _send_error(websocket, ErrorReason.INVALID_ACTION, "the game is not over")
                    continue
                if analysis_cache is None or analysis_cache[0] is not game:
                    # Off the event loop: the worst case is ~1s. Safe because a finished game no longer changes.
                    analyses = await asyncio.to_thread(turn_analyses, game)
                    analysis_cache = (game, serialize_analysis(analyses))
                reply = AnalysisMsg(protocol_version=PROTOCOL_VERSION, turns=analysis_cache[1])
                await websocket.send_json(reply.to_json())
                continue
            try:
                _apply_action(game, data)
            except ActionError as exc:
                await _send_error(websocket, exc.reason, exc.message)
                continue
            series_game_recorded = await _broadcast_and_run_bots(
                websocket, game, series, bot_difficulty, series_game_recorded
            )
    except WebSocketDisconnect:
        pass


mount_frontend(app, FRONTEND_DIST)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
