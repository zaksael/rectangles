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
        ws.receive_json()  # initial state broadcast

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
        ws.receive_json()  # initial state broadcast

        ws.send_json({"protocolVersion": 1})
        assert ws.receive_json()["reason"] == "malformedMessage"


def test_ws_rejects_message_with_wrong_protocol_version():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state broadcast

        ws.send_json({"protocolVersion": 2, "type": "roll"})
        reply = ws.receive_json()
        assert reply["reason"] == "protocolVersionMismatch"

        # connection is still open
        ws.send_json({"protocolVersion": 2, "type": "roll"})
        assert ws.receive_json()["reason"] == "protocolVersionMismatch"


def test_ws_connect_sends_initial_state():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        reply = ws.receive_json()
        assert reply["type"] == "state"
        game = reply["game"]
        assert game["board"]["size"] == 19
        assert game["board"]["skipLimit"] == 5
        assert game["turn"]["currentPlayerId"] == 1
        assert game["turn"]["turnState"] == "awaitingRoll"
        assert game["turn"]["lastRoll"] is None
        assert game["gameOver"]["reason"] is None


def test_ws_connect_honors_board_size_and_skip_limit_params():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&boardSize=23&skipLimit=3") as ws:
        game = ws.receive_json()["game"]
        assert game["board"]["size"] == 23
        assert game["board"]["skipLimit"] == 3


def test_ws_roll_broadcasts_new_state():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state

        ws.send_json({"protocolVersion": 1, "type": "roll"})
        reply = ws.receive_json()
        assert reply["type"] == "state"
        turn = reply["game"]["turn"]
        assert turn["lastRoll"] is not None
        assert turn["turnState"] != "awaitingRoll"


def test_ws_roll_in_wrong_state_returns_invalid_action():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state
        ws.send_json({"protocolVersion": 1, "type": "roll"})
        ws.receive_json()  # state after first roll

        # rolling again before the turn resolves is not legal
        ws.send_json({"protocolVersion": 1, "type": "roll"})
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert reply["reason"] == "invalidAction"

