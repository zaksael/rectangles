import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.game import Game, TurnState
from rectangles.ui.net_adapter import ServerGameAdapter
from server.app import ActionError, _apply_action, _bot_turn_step, app, run_in_background
from server.schema import ErrorReason


def test_run_in_background_serves_and_stops():
    url, stop = run_in_background()
    try:
        adapter = ServerGameAdapter(f"{url}?protocolVersion=1")
        assert adapter.board.size == 19
        adapter.close()
    finally:
        stop()

    with pytest.raises((ConnectionError, OSError)):
        ServerGameAdapter(f"{url}?protocolVersion=1")


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
        "protocolVersion=1&wildcardEnabled=1",
        "protocolVersion=1&wildcardEnabled=maybe",
        "protocolVersion=1&rerollEnabled=1",
        "protocolVersion=1&rerollEnabled=maybe",
        "protocolVersion=1&wallsEnabled=1",
        "protocolVersion=1&obstaclesEnabled=1",
        "protocolVersion=1&prizeEnabled=1",
        "protocolVersion=1&prizePoints=abc",
        "protocolVersion=1&pitfallEnabled=1",
        "protocolVersion=1&pitfallPoints=abc",
        "protocolVersion=1&stealEnabled=1",
        "protocolVersion=1&stealPoints=abc",
        "protocolVersion=1&selfEnclosedPenaltyEnabled=1",
        "protocolVersion=1&comebackNudgeEnabled=1",
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


def test_ws_connect_honors_wildcard_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&wildcardEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["wildcard"]["enabled"] is True


def test_ws_connect_honors_reroll_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&rerollEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["reroll"]["enabled"] is True


def test_ws_connect_honors_walls_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&wallsEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["walls"]["enabled"] is True


def test_ws_connect_honors_obstacles_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&obstaclesEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["obstacles"]["enabled"] is True


def test_ws_connect_honors_prize_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&prizeEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["prize"]["enabled"] is True


def test_ws_connect_honors_prize_points_param():
    client = TestClient(app)
    with client.websocket_connect(
        "/ws?protocolVersion=1&prizeEnabled=true&prizePoints=25"
    ) as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["prize"]["points"] == 25


def test_ws_connect_honors_pitfall_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&pitfallEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["pitfall"]["enabled"] is True


def test_ws_connect_honors_pitfall_points_param():
    client = TestClient(app)
    with client.websocket_connect(
        "/ws?protocolVersion=1&pitfallEnabled=true&pitfallPoints=25"
    ) as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["pitfall"]["points"] == 25


def test_ws_connect_honors_steal_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&stealEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["steal"]["enabled"] is True


def test_ws_connect_honors_steal_points_param():
    client = TestClient(app)
    with client.websocket_connect(
        "/ws?protocolVersion=1&stealEnabled=true&stealPoints=25"
    ) as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["steal"]["points"] == 25


def test_ws_connect_honors_self_enclosed_penalty_enabled_param():
    client = TestClient(app)
    with client.websocket_connect(
        "/ws?protocolVersion=1&selfEnclosedPenaltyEnabled=true"
    ) as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["selfEnclosedPenalty"]["enabled"] is True


def test_ws_connect_honors_comeback_nudge_enabled_param():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&comebackNudgeEnabled=true") as ws:
        game = ws.receive_json()["game"]
        assert game["houseRules"]["comebackNudge"]["enabled"] is True


def test_ws_connect_with_series_length_starts_a_series():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&seriesLength=3") as ws:
        series = ws.receive_json()["series"]
        assert series["length"] == 3
        assert series["gamesPlayed"] == 0
        assert series["isComplete"] is False


def test_ws_connect_without_series_length_has_no_series():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        assert ws.receive_json()["series"] is None


def test_ws_records_finished_round_into_series():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&seriesLength=3") as ws:
        ws.receive_json()
        ws.send_json({"protocolVersion": 1, "type": "surrender"})
        series = ws.receive_json()["series"]
        assert series["gamesPlayed"] == 1
        assert len(series["rounds"]) == 1


def test_ws_continue_series_starts_a_fresh_game():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&seriesLength=3&boardSize=19") as ws:
        first_game = ws.receive_json()["game"]
        ws.send_json({"protocolVersion": 1, "type": "surrender"})
        ws.receive_json()
        ws.send_json({"protocolVersion": 1, "type": "continueSeries"})
        reply = ws.receive_json()
        next_game = reply["game"]
        assert next_game["gameOver"]["reason"] is None
        assert next_game["players"]["1"]["board"]["pieces"] == []
        assert reply["series"]["gamesPlayed"] == 1


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


def test_apply_action_choose_wildcard_in_wrong_state_raises_invalid_action():
    game = Game(board_size=19, wildcard_enabled=True)

    with pytest.raises(ActionError) as exc_info:
        _apply_action(game, {"protocolVersion": 1, "type": "chooseWildcard", "value": 4})
    assert exc_info.value.reason == ErrorReason.INVALID_ACTION


def test_apply_action_choose_wildcard_illegal_value_raises_illegal_wildcard_value():
    game = Game(board_size=19, wildcard_enabled=True)
    game.state = TurnState.CHOOSING_WILDCARD
    game.last_roll = (6, 6)
    game.wildcard_index = 0

    with pytest.raises(ActionError) as exc_info:
        _apply_action(game, {"protocolVersion": 1, "type": "chooseWildcard", "value": 9})
    assert exc_info.value.reason == ErrorReason.ILLEGAL_WILDCARD_VALUE


def test_apply_action_choose_wildcard_success_resolves_roll():
    game = Game(board_size=19, wildcard_enabled=True)
    game.state = TurnState.CHOOSING_WILDCARD
    game.last_roll = (6, 6)
    game.wildcard_index = 0

    _apply_action(game, {"protocolVersion": 1, "type": "chooseWildcard", "value": 1})

    assert game.state in (TurnState.CHOOSING_PLACEMENT, TurnState.SKIPPED)
    assert game.last_roll == (1, 6)


def test_ws_choose_wildcard_before_roll_returns_invalid_action():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&wildcardEnabled=true") as ws:
        ws.receive_json()  # initial state

        ws.send_json({"protocolVersion": 1, "type": "chooseWildcard", "value": 4})
        reply = ws.receive_json()
        assert reply["type"] == "error"
        assert reply["reason"] == "invalidAction"


def test_apply_action_reroll_in_wrong_state_raises_invalid_action():
    game = Game(board_size=19, reroll_enabled=True)

    with pytest.raises(ActionError) as exc_info:
        _apply_action(game, {"protocolVersion": 1, "type": "reroll"})
    assert exc_info.value.reason == ErrorReason.INVALID_ACTION


def test_apply_action_reroll_commits_charge_and_rerolls():
    game = Game(board_size=19, reroll_enabled=True)
    game.state = TurnState.SKIPPED
    game.last_roll = (6, 6)

    _apply_action(game, {"protocolVersion": 1, "type": "reroll"})

    assert game.players[PLAYER_1].rerolls_used == 1
    assert game.last_roll is not None


def test_bot_turn_step_rerolls_from_skipped_instead_of_confirming():
    game = Game(board_size=19, reroll_enabled=True)
    game.current_player_id = PLAYER_2
    game.state = TurnState.SKIPPED
    game.last_roll = (6, 6)

    result = _bot_turn_step(game, "Blocking")

    assert result is True
    assert game.players[PLAYER_2].rerolls_used == 1
    assert len(game.history) == 0  # no skip was committed


def test_bot_turn_step_rerolls_from_choosing_placement_instead_of_placing():
    # PLAYER_1 hasn't moved, so its frontier is empty and Blocking's
    # blocking_score is 0 for every candidate - a guaranteed "bad roll".
    game = Game(board_size=19, reroll_enabled=True)
    game.current_player_id = PLAYER_2
    game.state = TurnState.CHOOSING_PLACEMENT
    game.last_roll = (1, 1)
    game.legal_cache = {(1, 1): {(5, 5)}}

    result = _bot_turn_step(game, "Blocking")

    assert result is True
    assert game.players[PLAYER_2].rerolls_used == 1
    assert len(game.players[PLAYER_2].pieces) == 0


def test_bot_turn_step_rerolls_from_choosing_wildcard_instead_of_picking():
    # PLAYER_1 hasn't moved, so Blocking's blocking_score is 0 for every
    # legal wildcard value - a guaranteed "bad roll".
    game = Game(board_size=19, reroll_enabled=True)
    game.current_player_id = PLAYER_2
    game.state = TurnState.CHOOSING_WILDCARD
    game.last_roll = (6, 6)
    game.wildcard_original_roll = (6, 6)
    game.wildcard_index = 0

    result = _bot_turn_step(game, "Blocking")

    assert result is True
    assert game.players[PLAYER_2].rerolls_used == 1


def test_ws_surrender_ends_game_and_declares_winner():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state

        ws.send_json({"protocolVersion": 1, "type": "surrender"})
        reply = ws.receive_json()
        assert reply["type"] == "state"
        game = reply["game"]
        assert game["turn"]["turnState"] == "gameOver"
        assert game["gameOver"]["reason"] == "surrender"
        assert game["gameOver"]["playerId"] == 1
        assert game["gameOver"]["winner"] == 2


def test_ws_surrender_twice_is_a_no_op():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state
        ws.send_json({"protocolVersion": 1, "type": "surrender"})
        ws.receive_json()  # state after first surrender

        ws.send_json({"protocolVersion": 1, "type": "surrender"})
        reply = ws.receive_json()
        assert reply["type"] == "state"
        assert reply["game"]["gameOver"]["reason"] == "surrender"


def test_ws_uncaught_exception_propagates_and_closes_connection(monkeypatch):
    # A genuine server-side bug (as opposed to a normal rule rejection like
    # ValueError -> invalidAction) must not be swallowed into a generic error
    # message - it propagates and the connection closes (M1_TASKS.md decision).
    def boom(self):
        raise RuntimeError("boom")

    monkeypatch.setattr(Game, "roll_dice", boom)
    client = TestClient(app)
    with pytest.raises(RuntimeError):
        with client.websocket_connect("/ws?protocolVersion=1") as ws:
            ws.receive_json()  # initial state
            ws.send_json({"protocolVersion": 1, "type": "roll"})
            ws.receive_json()


def test_ws_bot_takes_its_turn_after_human_places():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1&botSeats=2") as ws:
        ws.receive_json()  # initial state
        top_left, width, height = _roll_then_first_legal_placement(ws)

        ws.send_json(
            {"protocolVersion": 1, "type": "place", "topLeft": top_left, "width": width, "height": height}
        )
        after_human_place = ws.receive_json()["game"]
        assert after_human_place["turn"]["currentPlayerId"] == 2
        assert after_human_place["turn"]["turnState"] == "awaitingRoll"

        after_bot_roll = ws.receive_json()["game"]
        assert after_bot_roll["turn"]["currentPlayerId"] == 2
        assert after_bot_roll["turn"]["lastRoll"] is not None

        after_bot_move = ws.receive_json()["game"]
        assert after_bot_move["turn"]["currentPlayerId"] == 1
        assert after_bot_move["turn"]["turnState"] == "awaitingRoll"
        assert len(after_bot_move["players"]["2"]["board"]["pieces"]) == 1


def test_ws_without_bot_seats_player_two_stays_human():
    client = TestClient(app)
    with client.websocket_connect("/ws?protocolVersion=1") as ws:
        ws.receive_json()  # initial state
        top_left, width, height = _roll_then_first_legal_placement(ws)

        ws.send_json(
            {"protocolVersion": 1, "type": "place", "topLeft": top_left, "width": width, "height": height}
        )
        reply = ws.receive_json()["game"]
        assert reply["turn"]["currentPlayerId"] == 2
        assert reply["turn"]["turnState"] == "awaitingRoll"
        assert reply["turn"]["lastRoll"] is None  # no auto-roll - player 2 is human here

