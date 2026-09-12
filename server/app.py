import os

from fastapi import FastAPI, WebSocket

from rectangles.constants import (
    BOARD_SIZE_PRESETS,
    BOT_DIFFICULTY_PRESETS,
    PLAYER_2,
    SERIES_LENGTH_PRESETS,
    SKIP_LIMIT_PRESETS,
)

HOST = os.environ.get("RECTANGLES_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RECTANGLES_SERVER_PORT", "8765"))

_PRESET_PARAMS = {
    "boardSize": BOARD_SIZE_PRESETS,
    "skipLimit": SKIP_LIMIT_PRESETS,
    "seriesLength": SERIES_LENGTH_PRESETS,
    "botSeats": (PLAYER_2,),
    "botDifficulty": BOT_DIFFICULTY_PRESETS,
}

app = FastAPI()


def _connect_params_valid(query_params) -> bool:
    if not set(query_params.keys()) <= _PRESET_PARAMS.keys():
        return False
    for name, presets in _PRESET_PARAMS.items():
        value = query_params.get(name)
        if value is None:
            continue
        cast = type(presets[0])
        if cast(value) not in presets:
            return False
    return True


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    if not _connect_params_valid(websocket.query_params):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
