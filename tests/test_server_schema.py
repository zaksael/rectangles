from server.schema import ErrorMsg, ErrorReason, PlaceMsg, RollMsg, SkipMsg, StateMsg, SurrenderMsg


def test_roll_msg():
    msg = RollMsg(protocol_version=1)
    assert msg.to_json() == {"protocolVersion": 1, "type": "roll"}
    assert RollMsg.from_json(msg.to_json()) == msg


def test_place_msg():
    msg = PlaceMsg(protocol_version=1, top_left=(2, 3), width=4, height=5)
    assert msg.to_json() == {
        "protocolVersion": 1,
        "type": "place",
        "topLeft": [2, 3],
        "width": 4,
        "height": 5,
    }
    assert PlaceMsg.from_json(msg.to_json()) == msg


def test_skip_msg():
    msg = SkipMsg(protocol_version=1)
    assert msg.to_json() == {"protocolVersion": 1, "type": "skip"}
    assert SkipMsg.from_json(msg.to_json()) == msg


def test_surrender_msg():
    msg = SurrenderMsg(protocol_version=1)
    assert msg.to_json() == {"protocolVersion": 1, "type": "surrender"}
    assert SurrenderMsg.from_json(msg.to_json()) == msg


def test_error_msg():
    msg = ErrorMsg(protocol_version=1, reason=ErrorReason.ILLEGAL_PLACEMENT, message="nope")
    assert msg.to_json() == {
        "protocolVersion": 1,
        "type": "error",
        "reason": "illegalPlacement",
        "message": "nope",
    }
    assert ErrorMsg.from_json(msg.to_json()) == msg


def test_state_msg():
    msg = StateMsg(protocol_version=1, game={"board": {"size": 19}})
    assert msg.to_json() == {
        "protocolVersion": 1,
        "type": "state",
        "game": {"board": {"size": 19}},
    }
    assert StateMsg.from_json(msg.to_json()) == msg
