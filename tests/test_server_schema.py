from rectangles.constants import PLAYER_1
from rectangles.game import Game, TurnState
from server.schema import (
    ChooseWildcardMsg,
    ErrorMsg,
    ErrorReason,
    PlaceMsg,
    RerollMsg,
    RollMsg,
    SkipMsg,
    StateMsg,
    SurrenderMsg,
    serialize_game,
)


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


def test_reroll_msg():
    msg = RerollMsg(protocol_version=1)
    assert msg.to_json() == {"protocolVersion": 1, "type": "reroll"}
    assert RerollMsg.from_json(msg.to_json()) == msg


def test_choose_wildcard_msg():
    msg = ChooseWildcardMsg(protocol_version=1, value=4)
    assert msg.to_json() == {"protocolVersion": 1, "type": "chooseWildcard", "value": 4}
    assert ChooseWildcardMsg.from_json(msg.to_json()) == msg


def test_serialize_game_reroll_enabled_and_can_reroll():
    game = Game(board_size=19, reroll_enabled=True)
    reroll = serialize_game(game)["houseRules"]["reroll"]
    assert reroll == {"enabled": True, "canReroll": True}


def test_serialize_game_player_reroll_used_and_limit():
    game = Game(board_size=19, reroll_enabled=True)
    game.players[PLAYER_1].rerolls_used = 1

    reroll = serialize_game(game)["players"]["1"]["houseRules"]["reroll"]

    assert reroll == {"used": 1, "limit": 2}  # REROLL_LIMIT, comeback nudge off


def test_serialize_game_player_reroll_limit_bumped_by_comeback_nudge():
    game = Game(board_size=19, reroll_enabled=True, comeback_nudge_enabled=True)
    game.players[PLAYER_1].comeback_nudge_granted = True

    reroll = serialize_game(game)["players"]["1"]["houseRules"]["reroll"]

    assert reroll["limit"] == 3  # REROLL_LIMIT (2) + COMEBACK_NUDGE_EXTRA_REROLLS (1)


def test_serialize_game_walls_enabled_and_edges():
    game = Game(board_size=19, walls_enabled=True)
    game.board.wall_edges = frozenset({frozenset({(0, 0), (1, 0)}), frozenset({(5, 5), (5, 6)})})

    walls = serialize_game(game)["houseRules"]["walls"]

    assert walls["enabled"] is True
    assert sorted(map(sorted, walls["edges"])) == [[[0, 0], [1, 0]], [[5, 5], [5, 6]]]


def test_serialize_game_walls_disabled_by_default():
    game = Game(board_size=19)
    walls = serialize_game(game)["houseRules"]["walls"]
    assert walls == {"enabled": False, "edges": []}


def test_serialize_game_obstacles_enabled_and_cells():
    game = Game(board_size=19, obstacles_enabled=True)
    game.board.set_obstacle_cells(frozenset({(3, 4), (9, 9)}))

    obstacles = serialize_game(game)["houseRules"]["obstacles"]

    assert obstacles["enabled"] is True
    assert sorted(obstacles["cells"]) == [[3, 4], [9, 9]]


def test_serialize_game_obstacles_disabled_by_default():
    game = Game(board_size=19)
    obstacles = serialize_game(game)["houseRules"]["obstacles"]
    assert obstacles == {"enabled": False, "cells": []}


def test_serialize_game_wildcard_disabled_by_default():
    game = Game(board_size=19)
    wildcard = serialize_game(game)["houseRules"]["wildcard"]
    assert wildcard == {"enabled": False, "originalRoll": None, "legalValues": [], "editableIndex": None}


def test_serialize_game_wildcard_enabled_outside_picker():
    game = Game(board_size=19, wildcard_enabled=True)
    wildcard = serialize_game(game)["houseRules"]["wildcard"]
    assert wildcard == {"enabled": True, "originalRoll": None, "legalValues": [], "editableIndex": None}


def test_serialize_game_wildcard_picker_open():
    game = Game(board_size=19, wildcard_enabled=True)
    game.board.place(game.players[PLAYER_1], (0, 0), w=1, h=1)
    game.state = TurnState.CHOOSING_WILDCARD
    game.last_roll = (6, 6)
    game.wildcard_original_roll = (6, 6)
    game.wildcard_index = 0

    wildcard = serialize_game(game)["houseRules"]["wildcard"]

    assert wildcard["enabled"] is True
    assert wildcard["originalRoll"] == [6, 6]
    assert wildcard["editableIndex"] == 0
    assert wildcard["legalValues"] == [v for v in range(1, 7) if game.wildcard_value_is_legal(v)]
    assert wildcard["legalValues"]


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
