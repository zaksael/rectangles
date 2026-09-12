from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


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
class SurrenderMsg(_NoPayloadMsg):
    _TYPE: ClassVar[str] = "surrender"


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
