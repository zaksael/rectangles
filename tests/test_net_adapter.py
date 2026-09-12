import threading
import time

import pytest
import uvicorn

from rectangles.ui.net_adapter import ServerGameAdapter
from server.app import app
from server.schema import PlaceMsg, RollMsg, SurrenderMsg


@pytest.fixture
def live_server_url():
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}/ws"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "call",
    [
        lambda a: a.roll_dice(),
        lambda a: a.attempt_place((0, 0), 1, 1),
        lambda a: a.confirm_skip(),
        lambda a: a.surrender(),
        lambda a: a.close(),
    ],
)
def test_adapter_core_loop_methods_not_yet_implemented(call, live_server_url):
    adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1")
    with pytest.raises(NotImplementedError):
        call(adapter)


def test_adapter_end_turn_is_a_local_no_op(live_server_url):
    # Game.end_turn() is folded into the server's place/skip handling
    # internally - the adapter keeps the method only so
    # ui/input_common.py's call sites don't change, and it never touches
    # the network.
    adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1")
    adapter.end_turn()  # must not raise


def test_adapter_populates_board_from_initial_broadcast(live_server_url):
    adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1")
    assert adapter.board.size == 19


def test_request_returns_first_reply_and_applies_state(live_server_url):
    adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1")
    reply = adapter._request(RollMsg(protocol_version=1))
    assert reply["type"] == "state"
    assert adapter.last_roll is not None


def test_request_unblocks_only_once_for_chained_bot_broadcasts(live_server_url):
    adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1&botSeats=2")
    roll_reply = adapter._request(RollMsg(protocol_version=1))
    entry = next(e for e in roll_reply["game"]["turn"]["legalPlacements"] if e["topLefts"])
    top_left, width, height = entry["topLefts"][0], entry["width"], entry["height"]

    place_reply = adapter._request(
        PlaceMsg(protocol_version=1, top_left=tuple(top_left), width=width, height=height)
    )
    # _request unblocks on the FIRST broadcast after the human's placement,
    # before the bot's chained turn has happened.
    assert place_reply["game"]["turn"]["currentPlayerId"] == 2

    # The bot's chained broadcast(s) arrive asynchronously and update the
    # shared state without a second _request call unblocking anything.
    for _ in range(50):
        if adapter.current_player_id == 1:
            break
        time.sleep(0.05)
    assert adapter.current_player_id == 1
    assert len(adapter.players[2].pieces) == 1


def test_surrender_routes_game_over_reason_and_player_id(live_server_url):
    adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1")
    adapter._request(SurrenderMsg(protocol_version=1))

    assert adapter.state.name == "GAME_OVER"
    assert adapter.game_over_reason.name == "SURRENDER"
    assert adapter.surrendered_player_id == 1
    assert adapter.blocked_player_id is None
    assert adapter.skipped_out_player_id is None
