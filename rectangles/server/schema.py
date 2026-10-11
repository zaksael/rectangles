from dataclasses import asdict, dataclass
from enum import Enum
from typing import ClassVar

from rectangles.engine.constants import DICE_MAX, DICE_MIN, PLAYER_1, PLAYER_2, CellKind
from rectangles.engine.game import Game, GameOverReason, TurnState
from rectangles.engine.models import Player
from rectangles.engine.series import RoundResult, Series

PROTOCOL_VERSION = 1

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


def _serialize_player(game: Game, player: Player, self_enclosed_counts: dict[int, int]) -> dict:
    potential = game.potential_stats(player)
    breakdown = game.score_breakdown(player)
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
            "totalScore": breakdown.total,
            "breakdown": asdict(breakdown),
            "potential": _potential(potential),
        },
        "houseRules": {
            "reroll": {"used": player.rerolls_used, "limit": game.effective_reroll_limit(player)},
            "comebackNudge": {"granted": player.comeback_nudge_granted},
            "selfEnclosedPenalty": {"cells": self_enclosed_counts.get(player.id, 0)},
            **{
                kind.value: {"captured": player.special_captures.get(kind, 0)}
                for kind in CellKind
            },
        },
    }


RECENT_TURNS = 6


def serialize_game(game: Game) -> dict:
    legal_placements = [
        {"width": w, "height": h, "topLefts": [list(cell) for cell in cells]}
        for (w, h), cells in game.legal_cache.items()
        if cells
    ]
    winner = game.winner() if game.state == TurnState.GAME_OVER else None
    self_enclosed_counts = (
        game.board.self_enclosed_cell_counts() if game.self_enclosed_penalty_enabled else {}
    )
    return {
        "board": {"size": game.board_size, "skipLimit": game.skip_limit},
        "turn": {
            "currentPlayerId": game.current_player_id,
            "turnState": _TURN_STATE_NAMES[game.state],
            "lastRoll": list(game.last_roll) if game.last_roll is not None else None,
            "legalPlacements": legal_placements,
            "recentTurns": _serialize_steps(game)[-RECENT_TURNS:],
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
            "comebackNudge": {"enabled": game.comeback_nudge_enabled},
            "walls": {
                "enabled": game.walls_enabled,
                "edges": [[list(cell) for cell in sorted(edge)] for edge in game.board.wall_edges],
            },
            "obstacles": {
                "enabled": game.obstacles_enabled,
                "cells": [list(cell) for cell in sorted(game.board.obstacle_cells)],
            },
            **{
                kind.value: {
                    "enabled": getattr(game, f"{kind.value}_enabled"),
                    "cells": [list(cell) for cell in sorted(game.board.cells_of_kind(kind))],
                    "points": game.points_for(kind),
                }
                for kind in CellKind
            },
            "selfEnclosedPenalty": {"enabled": game.self_enclosed_penalty_enabled},
        },
        "players": {
            "1": _serialize_player(game, game.players[1], self_enclosed_counts),
            "2": _serialize_player(game, game.players[2], self_enclosed_counts),
        },
        "gameOver": {
            "reason": _GAME_OVER_REASON_NAMES.get(game.game_over_reason),
            "playerId": game.blocked_player_id or game.skipped_out_player_id or game.surrendered_player_id,
            "winner": winner,
            "history": _serialize_history(game) if game.state == TurnState.GAME_OVER else None,
        },
    }


def _serialize_history(game: Game) -> list[dict]:
    return [
        {**{k: v for k, v in step.items() if k not in ("turn", "points")}, "potential": _by_player({pid: _potential(p) for pid, p in potential.items()})}
        for step, potential in zip(_serialize_steps(game), game.potential_history())
    ]


def _potential(stats: dict[str, int]) -> dict:
    return {"area": stats["area"], "prize": {"points": stats["prize_points"]}}


def _serialize_steps(game: Game) -> list[dict]:
    """One entry per history record; `turn` is its 1-based move number, `points` the mover's own score change."""
    breakdowns = game.score_breakdown_history()
    steps = []
    for i, (record, breakdown) in enumerate(zip(game.history, breakdowns)):
        before = breakdowns[i - 1][record.player_id].total if i else 0
        steps.append(
            {
                "turn": i + 1,
                "playerId": record.player_id,
                "roll": list(record.roll),
                "placed": (
                    None
                    if record.placed is None
                    else {"topLeft": list(record.placed.top_left), "width": record.placed.width, "height": record.placed.height}
                ),
                "wildcardOriginalRoll": list(record.wildcard_original_roll) if record.wildcard_original_roll else None,
                "score": _by_player({pid: parts.total for pid, parts in breakdown.items()}),
                "breakdown": _by_player({pid: asdict(parts) for pid, parts in breakdown.items()}),
                "points": breakdown[record.player_id].total - before,
            }
        )
    return steps


def _by_player(values: dict[int, object]) -> dict:
    return {"1": values[PLAYER_1], "2": values[PLAYER_2]}


def _serialize_round(round_result: RoundResult) -> dict:
    return {
        "area": _by_player(round_result.area),
        "prizeCaptured": _by_player(round_result.prize_captured),
        "pitfallCaptured": _by_player(round_result.pitfall_captured),
        "stealCaptured": _by_player(round_result.steal_captured),
        "total": _by_player(round_result.total),
    }


def serialize_series(series: Series) -> dict:
    return {
        "length": series.length,
        "scores": _by_player(series.scores),
        "gamesPlayed": series.games_played,
        "rounds": [_serialize_round(r) for r in series.rounds],
        "isComplete": series.is_complete(),
        "winner": series.winner(),
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
    series: dict | None = None

    def to_json(self) -> dict:
        return {
            "protocolVersion": self.protocol_version,
            "type": "state",
            "game": self.game,
            "series": self.series,
        }

    @classmethod
    def from_json(cls, data: dict) -> "StateMsg":
        return cls(protocol_version=data["protocolVersion"], game=data["game"], series=data["series"])


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
