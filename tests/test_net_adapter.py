import pytest

from rectangles.ui.net_adapter import ServerGameAdapter


def test_adapter_starts_with_no_state_until_first_broadcast():
    adapter = ServerGameAdapter("ws://127.0.0.1:8765/ws?protocolVersion=1")
    fields = {k: v for k, v in vars(adapter).items() if k != "url"}
    assert fields and all(v is None for v in fields.values())


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
def test_adapter_core_loop_methods_not_yet_implemented(call):
    adapter = ServerGameAdapter("ws://127.0.0.1:8765/ws?protocolVersion=1")
    with pytest.raises(NotImplementedError):
        call(adapter)


def test_adapter_end_turn_is_a_local_no_op():
    # Game.end_turn() is folded into the server's place/skip handling
    # internally - the adapter keeps the method only so
    # ui/input_common.py's call sites don't change, and it never touches
    # the network.
    adapter = ServerGameAdapter("ws://127.0.0.1:8765/ws?protocolVersion=1")
    adapter.end_turn()  # must not raise
