import os

from fastapi import FastAPI, WebSocket

HOST = os.environ.get("RECTANGLES_SERVER_HOST", "127.0.0.1")
PORT = int(os.environ.get("RECTANGLES_SERVER_PORT", "8765"))

app = FastAPI()


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
