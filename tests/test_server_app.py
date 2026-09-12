from starlette.testclient import TestClient

from server.app import app


def test_ws_accepts_and_closes():
    client = TestClient(app)
    with client.websocket_connect("/ws"):
        pass
