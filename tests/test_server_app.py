import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.app import app


def test_ws_accepts_and_closes():
    client = TestClient(app)
    with client.websocket_connect("/ws"):
        pass


@pytest.mark.parametrize(
    "query",
    [
        "boardSize=20",
        "skipLimit=4",
        "seriesLength=4",
        "botSeats=1",
        "botSeats=2&botDifficulty=Expert",
        "wildcard=1",
    ],
)
def test_ws_rejects_invalid_connect_params(query):
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws?{query}"):
            pass
