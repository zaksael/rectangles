from __future__ import annotations

import json
import os
from pathlib import Path

from .constants import FLAG_BONUS_POINTS
from .game import Game, GameOverReason, TurnState
from .models import Player, Rectangle, TurnRecord
from .series import RoundResult, Series

SAVE_FORMAT_VERSION = 2
SAVE_DIR = Path.home() / ".rectangles_game"
DEFAULT_SAVE_PATH = SAVE_DIR / "save.json"


def _rect_to_dict(rect: Rectangle) -> dict:
    return {"top_left": list(rect.top_left), "width": rect.width, "height": rect.height}


def _rect_from_dict(data: dict, owner: int) -> Rectangle:
    return Rectangle(
        top_left=tuple(data["top_left"]),
        width=data["width"],
        height=data["height"],
        owner=owner,
    )


def _wall_edges_to_list(wall_edges: frozenset[frozenset[tuple[int, int]]]) -> list:
    return [[list(cell) for cell in edge] for edge in wall_edges]


def _wall_edges_from_list(data: list) -> frozenset[frozenset[tuple[int, int]]]:
    return frozenset(frozenset(tuple(cell) for cell in edge) for edge in data)


def _round_to_dict(round_result: RoundResult) -> dict:
    return {
        "area": round_result.area,
        "flags_captured": round_result.flags_captured,
        "total": round_result.total,
    }


def _round_from_dict(data: dict) -> RoundResult:
    return RoundResult(
        area={int(player_id): value for player_id, value in data["area"].items()},
        flags_captured={int(player_id): value for player_id, value in data["flags_captured"].items()},
        total={int(player_id): value for player_id, value in data["total"].items()},
    )


def _series_to_dict(series: Series) -> dict:
    return {
        "length": series.length,
        "board_size": series.board_size,
        "skip_limit": series.skip_limit,
        "flag_conquest_enabled": series.flag_conquest_enabled,
        "flag_bonus_points": series.flag_bonus_points,
        "walls_enabled": series.walls_enabled,
        "obstacles_enabled": series.obstacles_enabled,
        "wildcard_enabled": series.wildcard_enabled,
        "self_enclosed_penalty_enabled": series.self_enclosed_penalty_enabled,
        "scores": series.scores,
        "games_played": series.games_played,
        "rounds": [_round_to_dict(r) for r in series.rounds],
    }


def _series_from_dict(data: dict) -> Series:
    series = Series(
        length=data["length"],
        board_size=data["board_size"],
        skip_limit=data["skip_limit"],
        flag_conquest_enabled=data.get("flag_conquest_enabled", False),
        flag_bonus_points=data.get("flag_bonus_points", FLAG_BONUS_POINTS),
        walls_enabled=data.get("walls_enabled", False),
        obstacles_enabled=data.get("obstacles_enabled", False),
        wildcard_enabled=data.get("wildcard_enabled", False),
        self_enclosed_penalty_enabled=data.get("self_enclosed_penalty_enabled", False),
    )
    series.scores = {int(player_id): score for player_id, score in data["scores"].items()}
    series.games_played = data["games_played"]
    series.rounds = [_round_from_dict(r) for r in data.get("rounds", [])]
    return series


def to_dict(game: Game, series: Series | None = None) -> dict:
    return {
        "version": SAVE_FORMAT_VERSION,
        "series": _series_to_dict(series) if series is not None else None,
        "board_size": game.board_size,
        "skip_limit": game.skip_limit,
        "flag_conquest_enabled": game.flag_conquest_enabled,
        "flag_bonus_points": game.flag_bonus_points,
        "flag_cells": [list(cell) for cell in game.board.flag_cells],
        "walls_enabled": game.walls_enabled,
        "wall_edges": _wall_edges_to_list(game.board.wall_edges),
        "obstacles_enabled": game.obstacles_enabled,
        "obstacle_cells": [list(cell) for cell in game.board.obstacle_cells],
        "wildcard_enabled": game.wildcard_enabled,
        "self_enclosed_penalty_enabled": game.self_enclosed_penalty_enabled,
        "current_player_id": game.current_player_id,
        "state": game.state.name,
        "last_roll": list(game.last_roll) if game.last_roll is not None else None,
        "wildcard_index": game.wildcard_index,
        "wildcard_original_roll": list(game.wildcard_original_roll)
        if game.wildcard_original_roll is not None
        else None,
        "game_over_reason": game.game_over_reason.name if game.game_over_reason is not None else None,
        "skipped_out_player_id": game.skipped_out_player_id,
        "blocked_player_id": game.blocked_player_id,
        "surrendered_player_id": game.surrendered_player_id,
        "players": {
            player.id: {
                "name": player.name,
                "start_corner": list(player.start_corner),
                "consecutive_skips": player.consecutive_skips,
                "flags_captured": player.flags_captured,
                "pieces": [_rect_to_dict(rect) for rect in player.pieces],
            }
            for player in game.players.values()
        },
        "history": [
            {
                "player_id": record.player_id,
                "roll": list(record.roll),
                "placed": _rect_to_dict(record.placed) if record.placed is not None else None,
                "wildcard_original_roll": list(record.wildcard_original_roll)
                if record.wildcard_original_roll is not None
                else None,
            }
            for record in game.history
        ],
    }


def from_dict(data: dict) -> tuple[Game, Series | None]:
    game = Game(
        board_size=data["board_size"],
        skip_limit=data["skip_limit"],
        flag_conquest_enabled=data.get("flag_conquest_enabled", False),
        flag_bonus_points=data.get("flag_bonus_points", FLAG_BONUS_POINTS),
        walls_enabled=data.get("walls_enabled", False),
        obstacles_enabled=data.get("obstacles_enabled", False),
        wildcard_enabled=data.get("wildcard_enabled", False),
        self_enclosed_penalty_enabled=data.get("self_enclosed_penalty_enabled", False),
    )
    if data.get("flag_cells") is not None:
        game.board.flag_cells = frozenset(tuple(cell) for cell in data["flag_cells"])
    if data.get("wall_edges") is not None:
        game.board.wall_edges = _wall_edges_from_list(data["wall_edges"])
    if data.get("obstacle_cells") is not None:
        game.board.set_obstacle_cells(frozenset(tuple(cell) for cell in data["obstacle_cells"]))

    for player_id_str, player_data in data["players"].items():
        player_id = int(player_id_str)
        player: Player = game.players[player_id]
        player.name = player_data["name"]
        player.start_corner = tuple(player_data["start_corner"])
        player.consecutive_skips = player_data["consecutive_skips"]
        player.flags_captured = player_data.get("flags_captured", 0)
        for piece_data in player_data["pieces"]:
            top_left = tuple(piece_data["top_left"])
            game.board.place(player, top_left, piece_data["width"], piece_data["height"])

    game.current_player_id = data["current_player_id"]
    game.state = TurnState[data["state"]]
    game.last_roll = tuple(data["last_roll"]) if data["last_roll"] is not None else None
    game.wildcard_index = data.get("wildcard_index")
    game.wildcard_original_roll = (
        tuple(data["wildcard_original_roll"]) if data.get("wildcard_original_roll") is not None else None
    )
    game.game_over_reason = (
        GameOverReason[data["game_over_reason"]] if data["game_over_reason"] is not None else None
    )
    game.skipped_out_player_id = data["skipped_out_player_id"]
    game.blocked_player_id = data["blocked_player_id"]
    game.surrendered_player_id = data["surrendered_player_id"]
    game.history = [
        TurnRecord(
            player_id=record["player_id"],
            roll=tuple(record["roll"]),
            placed=_rect_from_dict(record["placed"], record["player_id"])
            if record["placed"] is not None
            else None,
            wildcard_original_roll=tuple(record["wildcard_original_roll"])
            if record.get("wildcard_original_roll") is not None
            else None,
        )
        for record in data["history"]
    ]

    if game.state == TurnState.CHOOSING_PLACEMENT:
        game.legal_cache = game.legal_placements_for_roll()

    series_data = data.get("series")
    series = _series_from_dict(series_data) if series_data is not None else None
    return game, series


def save_game(game: Game, series: Series | None = None, path: Path = DEFAULT_SAVE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(to_dict(game, series)))
    os.replace(tmp_path, path)


def load_game(path: Path = DEFAULT_SAVE_PATH) -> tuple[Game, Series | None] | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("version") != SAVE_FORMAT_VERSION:
        return None
    try:
        return from_dict(data)
    except (KeyError, TypeError, ValueError):
        return None


def has_save(path: Path = DEFAULT_SAVE_PATH) -> bool:
    return path.exists() and path.is_file()


def delete_save(path: Path = DEFAULT_SAVE_PATH) -> None:
    path.unlink(missing_ok=True)


def has_game_in_progress(game: Game | None) -> bool:
    return game is not None and game.state != TurnState.GAME_OVER and bool(game.history)


def should_save_on_exit(game: Game | None, series: Series | None) -> bool:
    # A just-finished round (state == GAME_OVER) still needs saving while its
    # series isn't decided yet, otherwise quitting from the game-over screen
    # silently drops the series tally.
    return has_game_in_progress(game) or (series is not None and not series.is_complete())
