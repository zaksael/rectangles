import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.app import app


def test_ws_accepts_and_closes():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1"):
        pass


@pytest.mark.parametrize(
    "query",
    [
        "protocolVersion=1&boardSize=20",
        "protocolVersion=1&skipLimit=4",
        "protocolVersion=1&seriesLength=4",
        "protocolVersion=1&botSeats=1",
        "protocolVersion=1&botSeats=2&botDifficulty=Expert",
        "protocolVersion=1&wildcard=1",
        "",
        "protocolVersion=2",
        "protocolVersion=1&boardSize=abc",
    ],
)
def test_ws_rejects_invalid_connect_params(query):
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws?{query}"):
            pass


def test_ws_replies_malformed_message_and_stays_open():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.send_text("not json")
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert reply["reason"] == "malformedMessage"

        # connection is still open: a second malformed message gets a second reply
        ws.send_text("also not json")
        assert ws.receive_json()["reason"] == "malformedMessage"


def test_ws_rejects_message_missing_type():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.send_json({"protocolVersion": 1})
        assert ws.receive_json()["reason"] == "malformedMessage"


def test_ws_rejects_message_with_wrong_protocol_version():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.send_json({"protocolVersion": 2, "type": "roll"})
        reply = ws.receive_json()
        assert reply["reason"] == "protocolVersionMismatch"

        # connection is still open
        ws.send_json({"protocolVersion": 2, "type": "roll"})
        assert ws.receive_json()["reason"] == "protocolVersionMismatch"
