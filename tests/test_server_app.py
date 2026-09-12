import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.game import Game, TurnState
from server.app import ActionError, _apply_action, app
from server.schema import ErrorReason


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


def _roll_then_first_legal_placement(ws):
    ws.send_json({"protocolVersion": 1, "type": "roll"})
    turn = ws.receive_json()["game"]["turn"]
    entry = next(e for e in turn["legalPlacements"] if e["topLefts"])
    return entry["topLefts"][0], entry["width"], entry["height"]


def test_ws_place_success_advances_turn():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state
        top_left, width, height = _roll_then_first_legal_placement(ws)

        ws.send_json(
            {"protocolVersion": 1, "type": "place", "topLeft": top_left, "width": width, "height": height}
        )
        reply = ws.receive_json()
        assert reply["type"] == "state"
        game = reply["game"]
        assert game["turn"]["currentPlayerId"] == 2
        assert game["turn"]["turnState"] == "awaitingRoll"
        pieces = game["players"]["1"]["board"]["pieces"]
        assert len(pieces) == 1
        assert pieces[0]["topLeft"] == top_left
        assert pieces[0]["width"] == width
        assert pieces[0]["height"] == height


def test_ws_place_illegal_returns_error():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state
        ws.send_json({"protocolVersion": 1, "type": "roll"})
        ws.receive_json()  # state after roll

        # far corner is never anchored to a fresh player's start corner
        ws.send_json(
            {"protocolVersion": 1, "type": "place", "topLeft": [18, 18], "width": 1, "height": 1}
        )
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert reply["reason"] == "illegalPlacement"


def test_ws_place_before_roll_returns_invalid_action():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state

        ws.send_json(
            {"protocolVersion": 1, "type": "place", "topLeft": [0, 0], "width": 1, "height": 1}
        )
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert reply["reason"] == "illegalPlacement"


def test_ws_skip_before_roll_returns_invalid_action():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state

        ws.send_json({"protocolVersion": 1, "type": "skip"})
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert reply["reason"] == "invalidAction"


def test_apply_action_skip_in_wrong_state_raises_invalid_action():
    game = Game(board_size=19)

    with pytest.raises(ActionError) as exc_info:
        _apply_action(game, {"protocolVersion": 1, "type": "skip"})
    assert exc_info.value.reason == ErrorReason.INVALID_ACTION


def test_apply_action_skip_commits_and_advances_turn():
    # reroll_enabled=True keeps can_reroll() true, matching the state
    # Game._resolve_roll() leaves an un-rerollable-but-not-yet-committed
    # skip in (see rectangles/game.py's Game.confirm_skip()).
    game = Game(board_size=19, reroll_enabled=True)
    game.board.place(game.players[PLAYER_1], (0, 0), w=1, h=1)  # has_moved, non-empty frontier
    game.state = TurnState.SKIPPED
    game.last_roll = (6, 6)

    _apply_action(game, {"protocolVersion": 1, "type": "skip"})

    assert game.players[PLAYER_1].consecutive_skips == 1
    assert len(game.history) == 1
    assert game.current_player_id == PLAYER_2
    assert game.state == TurnState.AWAITING_ROLL

