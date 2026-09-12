import time

import pytest

from rectangles.ui.net_adapter import ServerGameAdapter
from server.app import run_in_background
from server.schema import PlaceMsg, RollMsg, SurrenderMsg


@pytest.fixture
def live_server_url():
    url, stop = run_in_background()
    try:
        yield url
    finally:
        stop()


@pytest.fixture
def make_adapter(live_server_url):
    adapters = []

    def factory(query: str = "") -> ServerGameAdapter:
        adapter = ServerGameAdapter(f"{live_server_url}?protocolVersion=1{query}")
        adapters.append(adapter)
        return adapter

    yield factory
    for adapter in adapters:
        adapter.close()


def test_check_game_over_is_a_local_no_op(make_adapter):
    # The server already folds check_game_over()+end_turn() into its
    # place/skip handling - see end_turn()'s own no-op for the same reason.
    adapter = make_adapter()
    assert adapter.check_game_over() is False


def test_can_reroll_is_always_false(make_adapter):
    # Reroll isn't wired server-side yet (Phase F) - no connect param
    # exists to enable it, so a server-backed game's real answer is always
    # False today.
    adapter = make_adapter()
    assert adapter.can_reroll() is False


def test_unreachable_server_raises_instead_of_hanging():
    with pytest.raises((ConnectionError, TimeoutError, OSError)):
        ServerGameAdapter("ws://127.0.0.1:1/ws?protocolVersion=1")


def test_close_stops_the_background_thread(make_adapter):
    adapter = make_adapter()

    adapter.close()

    assert not adapter._thread.is_alive()


def test_adapter_end_turn_is_a_local_no_op(make_adapter):
    # Game.end_turn() is folded into the server's place/skip handling
    # internally - the adapter keeps the method only so
    # ui/input_common.py's call sites don't change, and it never touches
    # the network.
    adapter = make_adapter()
    adapter.end_turn()  # must not raise


def test_adapter_populates_board_from_initial_broadcast(make_adapter):
    adapter = make_adapter()
    assert adapter.board.size == 19


def test_roll_dice_returns_last_roll_on_success(make_adapter):
    adapter = make_adapter()
    roll = adapter.roll_dice()
    assert roll == adapter.last_roll
    assert adapter.state.name in ("CHOOSING_PLACEMENT", "SKIPPED", "CHOOSING_WILDCARD")


def test_roll_dice_in_wrong_state_raises_value_error(make_adapter):
    adapter = make_adapter()
    adapter.roll_dice()
    with pytest.raises(ValueError):
        adapter.roll_dice()


def test_attempt_place_returns_true_on_success(make_adapter):
    adapter = make_adapter()
    adapter.roll_dice()
    entry = next(e for e in adapter.legal_cache.items() if e[1])
    (width, height), top_lefts = entry
    top_left = next(iter(top_lefts))

    result = adapter.attempt_place(top_left, width, height)

    assert result is True
    assert len(adapter.players[1].pieces) == 1


def test_attempt_place_illegal_returns_false(make_adapter):
    adapter = make_adapter()
    adapter.roll_dice()

    # far corner is never anchored to a fresh player's start corner
    result = adapter.attempt_place((18, 18), 1, 1)

    assert result is False


def test_confirm_skip_before_roll_raises_value_error(make_adapter):
    adapter = make_adapter()
    with pytest.raises(ValueError):
        adapter.confirm_skip()


def test_surrender_ends_game_without_raising(make_adapter):
    adapter = make_adapter()

    result = adapter.surrender()

    assert result is None
    assert adapter.state.name == "GAME_OVER"


def test_request_returns_first_reply_and_applies_state(make_adapter):
    adapter = make_adapter()
    reply = adapter._request(RollMsg(protocol_version=1))
    assert reply["type"] == "state"
    assert adapter.last_roll is not None


def test_request_unblocks_only_once_for_chained_bot_broadcasts(make_adapter):
    adapter = make_adapter("&botSeats=2")
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


def test_surrender_routes_game_over_reason_and_player_id(make_adapter):
    adapter = make_adapter()
    adapter._request(SurrenderMsg(protocol_version=1))

    assert adapter.state.name == "GAME_OVER"
    assert adapter.game_over_reason.name == "SURRENDER"
    assert adapter.surrendered_player_id == 1
    assert adapter.blocked_player_id is None
    assert adapter.skipped_out_player_id is None
