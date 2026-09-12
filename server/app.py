import json
import os

from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect

from rectangles.constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    PLAYER_2,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
)
from server.schema import ErrorMsg, ErrorReason

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

app = FastAPI()


def _connect_params_valid(query_params) -> bool:
    if "protocolVersion" not in query_params:
        return False
    if not set(query_params.keys()) <= _PRESET_PARAMS.keys():
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
    return True


async def _send_error(websocket: WebSocket, reason: ErrorReason, message: str) -> None:
    error = ErrorMsg(protocol_version=PROTOCOL_VERSION, reason=reason, message=message)
    await websocket.send_json(error.to_json())


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    if not _connect_params_valid(websocket.query_params):
        await websocket.close(code=1008)
        return
    await websocket.accept()
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
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
