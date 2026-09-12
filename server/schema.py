from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from rectangles.constants import DICE_MAX, DICE_MIN
from rectangles.game import Game, GameOverReason, TurnState
from rectangles.models import Player

_TURN_STATE_NAMES = {
    TurnState.AWAITING_ROLL: "awaitingRoll",
    TurnState.CHOOSING_WILDCARD: "choosingWildcard",
    TurnState.CHOOSING_PLACEMENT: "choosingPlacement",
    TurnState.SKIPPED: "skipped",
    TurnState.GAME_OVER: "gameOver",
}

_GAME_OVER_REASON_NAMES = {
    GameOverReason.BOARD_FULL: "boardFull",
    GameOverReason.SKIP_LIMIT: "skipLimit",
    GameOverReason.PLAYER_BLOCKED: "playerBlocked",
    GameOverReason.SURRENDER: "surrender",
}


def _serialize_player(game: Game, player: Player) -> dict:
    potential = game.potential_stats(player)
    return {
        "name": player.name,
        "board": {
            "startCorner": list(player.start_corner),
            "pieces": [
                {"topLeft": list(p.top_left), "width": p.width, "height": p.height, "owner": p.owner}
                for p in player.pieces
            ],
            "consecutiveSkips": player.consecutive_skips,
        },
        "score": {
            "totalArea": player.total_area,
            "totalScore": game.total_score(player),
            "potential": {"area": potential["area"], "prize": {"points": potential["prize_points"]}},
        },
        "houseRules": {
            "reroll": {"used": player.rerolls_used, "limit": game.effective_reroll_limit(player)},
            "comebackNudge": {"granted": player.comeback_nudge_granted},
            "selfEnclosedPenalty": {"cells": 0},
            "prize": {"captured": 0},
            "pitfall": {"captured": 0},
            "steal": {"captured": 0},
        },
    }


def serialize_game(game: Game) -> dict:
    legal_placements = [
        {"width": w, "height": h, "topLefts": [list(cell) for cell in cells]}
        for (w, h), cells in game.legal_cache.items()
        if cells
    ]
    winner = game.winner() if game.state == TurnState.GAME_OVER else None
    return {
        "board": {"size": game.board_size, "skipLimit": game.skip_limit},
        "turn": {
            "currentPlayerId": game.current_player_id,
            "turnState": _TURN_STATE_NAMES[game.state],
            "lastRoll": list(game.last_roll) if game.last_roll is not None else None,
            "legalPlacements": legal_placements,
        },
        "houseRules": {
            "wildcard": {
                "enabled": game.wildcard_enabled,
                "originalRoll": list(game.wildcard_original_roll) if game.wildcard_original_roll else None,
                "legalValues": [
                    v for v in range(DICE_MIN, DICE_MAX + 1) if game.wildcard_value_is_legal(v)
                ]
                if game.wildcard_index is not None
                else [],
                "editableIndex": game.wildcard_index,
            },
            "reroll": {"enabled": game.reroll_enabled, "canReroll": game.can_reroll()},
            "comebackNudge": {"enabled": False},
            "walls": {"enabled": False, "edges": []},
            "obstacles": {"enabled": False, "cells": []},
            "prize": {"enabled": False, "cells": [], "points": 0},
            "pitfall": {"enabled": False, "cells": [], "points": 0},
            "steal": {"enabled": False, "cells": [], "points": 0},
            "selfEnclosedPenalty": {"enabled": False},
        },
        "players": {
            "1": _serialize_player(game, game.players[1]),
            "2": _serialize_player(game, game.players[2]),
        },
        "gameOver": {
            "reason": _GAME_OVER_REASON_NAMES.get(game.game_over_reason),
            "playerId": game.blocked_player_id or game.skipped_out_player_id or game.surrendered_player_id,
            "winner": winner,
        },
    }


@dataclass(frozen=True)
class _NoPayloadMsg:
    _TYPE: ClassVar[str] = ""

    protocol_version: int

    def to_json(self) -> dict:
        return {"protocolVersion": self.protocol_version, "type": self._TYPE}

    @classmethod
    def from_json(cls, data: dict) -> "_NoPayloadMsg":
        return cls(protocol_version=data["protocolVersion"])


@dataclass(frozen=True)
class RollMsg(_NoPayloadMsg):
    _TYPE: ClassVar[str] = "roll"


@dataclass(frozen=True)
class SkipMsg(_NoPayloadMsg):
    _TYPE: ClassVar[str] = "skip"


@dataclass(frozen=True)
class RerollMsg(_NoPayloadMsg):
    _TYPE: ClassVar[str] = "reroll"


@dataclass(frozen=True)
class SurrenderMsg(_NoPayloadMsg):
    _TYPE: ClassVar[str] = "surrender"


@dataclass(frozen=True)
class ChooseWildcardMsg:
    protocol_version: int
    value: int

    def to_json(self) -> dict:
        return {"protocolVersion": self.protocol_version, "type": "chooseWildcard", "value": self.value}

    @classmethod
    def from_json(cls, data: dict) -> "ChooseWildcardMsg":
        return cls(protocol_version=data["protocolVersion"], value=data["value"])


@dataclass(frozen=True)
class StateMsg:
    protocol_version: int
    game: dict

    def to_json(self) -> dict:
        return {"protocolVersion": self.protocol_version, "type": "state", "game": self.game}

    @classmethod
    def from_json(cls, data: dict) -> "StateMsg":
        return cls(protocol_version=data["protocolVersion"], game=data["game"])


class ErrorReason(str, Enum):
    INVALID_ACTION = "invalidAction"
    ILLEGAL_PLACEMENT = "illegalPlacement"
    PROTOCOL_VERSION_MISMATCH = "protocolVersionMismatch"
    ILLEGAL_WILDCARD_VALUE = "illegalWildcardValue"
    MALFORMED_MESSAGE = "malformedMessage"


@dataclass(frozen=True)
class ErrorMsg:
    protocol_version: int
    reason: ErrorReason
    message: str

    def to_json(self) -> dict:
        return {
            "protocolVersion": self.protocol_version,
            "type": "error",
            "reason": self.reason.value,
            "message": self.message,
        }

    @classmethod
    def from_json(cls, data: dict) -> "ErrorMsg":
        return cls(
            protocol_version=data["protocolVersion"],
            reason=ErrorReason(data["reason"]),
            message=data["message"],
        )


@dataclass(frozen=True)
class PlaceMsg:
    protocol_version: int
    top_left: tuple[int, int]
    width: int
    height: int

    def to_json(self) -> dict:
        return {
            "protocolVersion": self.protocol_version,
            "type": "place",
            "topLeft": list(self.top_left),
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_json(cls, data: dict) -> "PlaceMsg":
        row, col = data["topLeft"]
        return cls(
            protocol_version=data["protocolVersion"],
            top_left=(row, col),
            width=data["width"],
            height=data["height"],
        )
