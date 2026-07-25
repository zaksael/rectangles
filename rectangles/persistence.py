from __future__ import annotations

import json
import os
from pathlib import Path

from .game import Game, GameOverReason, TurnState
from .models import Player, Rectangle, TurnRecord

SAVE_FORMAT_VERSION = 1
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


def to_dict(game: Game) -> dict:
    return {
        "version": SAVE_FORMAT_VERSION,
        "board_size": game.board_size,
        "skip_limit": game.skip_limit,
        "current_player_id": game.current_player_id,
        "state": game.state.name,
        "last_roll": list(game.last_roll) if game.last_roll is not None else None,
        "game_over_reason": game.game_over_reason.name if game.game_over_reason is not None else None,
        "skipped_out_player_id": game.skipped_out_player_id,
        "blocked_player_id": game.blocked_player_id,
        "surrendered_player_id": game.surrendered_player_id,
        "players": {
            str(player.id): {
                "name": player.name,
                "start_corner": list(player.start_corner),
                "consecutive_skips": player.consecutive_skips,
                "pieces": [_rect_to_dict(rect) for rect in player.pieces],
            }
            for player in game.players.values()
        },
        "history": [
            {
                "player_id": record.player_id,
                "roll": list(record.roll),
                "placed": _rect_to_dict(record.placed) if record.placed is not None else None,
            }
            for record in game.history
        ],
    }


def from_dict(data: dict) -> Game:
    game = Game(board_size=data["board_size"], skip_limit=data["skip_limit"])

    for player_id_str, player_data in data["players"].items():
        player_id = int(player_id_str)
        player: Player = game.players[player_id]
        player.name = player_data["name"]
        player.start_corner = tuple(player_data["start_corner"])
        player.consecutive_skips = player_data["consecutive_skips"]
        for piece_data in player_data["pieces"]:
            top_left = tuple(piece_data["top_left"])
            game.board.place(player, top_left, piece_data["width"], piece_data["height"])

    game.current_player_id = data["current_player_id"]
    game.state = TurnState[data["state"]]
    game.last_roll = tuple(data["last_roll"]) if data["last_roll"] is not None else None
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
        )
        for record in data["history"]
    ]

    if game.state == TurnState.CHOOSING_PLACEMENT:
        game.legal_cache = game.legal_placements_for_roll()

    return game


def save_game(game: Game, path: Path = DEFAULT_SAVE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(to_dict(game)))
    os.replace(tmp_path, path)


def load_game(path: Path = DEFAULT_SAVE_PATH) -> Game | None:
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
