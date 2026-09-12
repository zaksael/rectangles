from __future__ import annotations

import json
import os
from pathlib import Path

from .constants import CellKind, PLAYER_1, PLAYER_2
from .game import Game, GameOverReason, TurnState
from .models import Cell, Player, Rectangle, SpecialCell, TurnRecord
from .series import RoundResult, Series
from .tournament import Bracket, Match, Participant

SAVE_FORMAT_VERSION = 3
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


def _special_cells_to_list(special_cells: frozenset[SpecialCell]) -> list:
    return [
        {"kind": sc.kind.value, "row": sc.location.row, "col": sc.location.col, "pair_id": sc.pair_id}
        for sc in special_cells
    ]


def _special_cells_from_list(data: list) -> frozenset[SpecialCell]:
    return frozenset(
        SpecialCell(kind=CellKind(d["kind"]), location=Cell(d["row"], d["col"]), pair_id=d["pair_id"])
        for d in data
    )


def _round_to_dict(round_result: RoundResult) -> dict:
    return {
        "area": round_result.area,
        "prize_captured": round_result.prize_captured,
        "pitfall_captured": round_result.pitfall_captured,
        "steal_captured": round_result.steal_captured,
        "total": round_result.total,
    }


def _round_from_dict(data: dict) -> RoundResult:
    zero = {PLAYER_1: 0, PLAYER_2: 0}
    return RoundResult(
        area={int(player_id): value for player_id, value in data["area"].items()},
        prize_captured={int(player_id): value for player_id, value in data["prize_captured"].items()},
        pitfall_captured={
            int(player_id): value for player_id, value in data.get("pitfall_captured", zero).items()
        },
        steal_captured={
            int(player_id): value for player_id, value in data.get("steal_captured", zero).items()
        },
        total={int(player_id): value for player_id, value in data["total"].items()},
    )


def _series_to_dict(series: Series) -> dict:
    return {
        "length": series.length,
        "board_size": series.board_size,
        "skip_limit": series.skip_limit,
        "prize_enabled": series.prize_enabled,
        "walls_enabled": series.walls_enabled,
        "obstacles_enabled": series.obstacles_enabled,
        "pitfall_enabled": series.pitfall_enabled,
        "steal_enabled": series.steal_enabled,
        "special_cell_points": series.special_cell_points,
        "wildcard_enabled": series.wildcard_enabled,
        "self_enclosed_penalty_enabled": series.self_enclosed_penalty_enabled,
        "reroll_enabled": series.reroll_enabled,
        "comeback_nudge_enabled": series.comeback_nudge_enabled,
        "scores": series.scores,
        "games_played": series.games_played,
        "rounds": [_round_to_dict(r) for r in series.rounds],
    }


def _series_from_dict(data: dict) -> Series:
    series = Series(
        length=data["length"],
        board_size=data["board_size"],
        skip_limit=data["skip_limit"],
        prize_enabled=data.get("prize_enabled", False),
        walls_enabled=data.get("walls_enabled", False),
        obstacles_enabled=data.get("obstacles_enabled", False),
        pitfall_enabled=data.get("pitfall_enabled", False),
        steal_enabled=data.get("steal_enabled", False),
        special_cell_points=data.get("special_cell_points", {}),
        wildcard_enabled=data.get("wildcard_enabled", False),
        self_enclosed_penalty_enabled=data.get("self_enclosed_penalty_enabled", False),
        reroll_enabled=data.get("reroll_enabled", False),
        comeback_nudge_enabled=data.get("comeback_nudge_enabled", False),
    )
    series.scores = {int(player_id): score for player_id, score in data["scores"].items()}
    series.games_played = data["games_played"]
    series.rounds = [_round_from_dict(r) for r in data.get("rounds", [])]
    return series


def _participant_to_dict(participant: Participant) -> dict:
    return {
        "name": participant.name,
        "is_bot": participant.is_bot,
        "bot_difficulty": participant.bot_difficulty,
    }


def _participant_from_dict(data: dict) -> Participant:
    return Participant(name=data["name"], is_bot=data["is_bot"], bot_difficulty=data["bot_difficulty"])


def _match_to_dict(match: Match) -> dict:
    return {
        "participant_a": match.participant_a,
        "participant_b": match.participant_b,
        "series": _series_to_dict(match.series) if match.series is not None else None,
        "tiebreak_game": _game_to_dict(match.tiebreak_game) if match.tiebreak_game is not None else None,
        "winner": match.winner,
    }


def _match_from_dict(data: dict) -> Match:
    return Match(
        participant_a=data["participant_a"],
        participant_b=data["participant_b"],
        series=_series_from_dict(data["series"]) if data.get("series") is not None else None,
        tiebreak_game=_game_from_dict(data["tiebreak_game"]) if data.get("tiebreak_game") is not None else None,
        winner=data.get("winner"),
    )


def _bracket_to_dict(bracket: Bracket) -> dict:
    return {
        "participants": [_participant_to_dict(p) for p in bracket.participants],
        "series_length": bracket.series_length,
        "board_size": bracket.board_size,
        "skip_limit": bracket.skip_limit,
        "prize_enabled": bracket.prize_enabled,
        "walls_enabled": bracket.walls_enabled,
        "obstacles_enabled": bracket.obstacles_enabled,
        "pitfall_enabled": bracket.pitfall_enabled,
        "steal_enabled": bracket.steal_enabled,
        "special_cell_points": bracket.special_cell_points,
        "wildcard_enabled": bracket.wildcard_enabled,
        "self_enclosed_penalty_enabled": bracket.self_enclosed_penalty_enabled,
        "reroll_enabled": bracket.reroll_enabled,
        "comeback_nudge_enabled": bracket.comeback_nudge_enabled,
        "rounds": [[_match_to_dict(m) for m in round_] for round_ in bracket.rounds],
        "current_match_index": bracket.current_match_index,
    }


def _bracket_from_dict(data: dict) -> Bracket:
    return Bracket(
        participants=[_participant_from_dict(p) for p in data["participants"]],
        series_length=data["series_length"],
        board_size=data["board_size"],
        skip_limit=data["skip_limit"],
        prize_enabled=data.get("prize_enabled", False),
        walls_enabled=data.get("walls_enabled", False),
        obstacles_enabled=data.get("obstacles_enabled", False),
        pitfall_enabled=data.get("pitfall_enabled", False),
        steal_enabled=data.get("steal_enabled", False),
        special_cell_points=data.get("special_cell_points", {}),
        wildcard_enabled=data.get("wildcard_enabled", False),
        self_enclosed_penalty_enabled=data.get("self_enclosed_penalty_enabled", False),
        reroll_enabled=data.get("reroll_enabled", False),
        comeback_nudge_enabled=data.get("comeback_nudge_enabled", False),
        rounds=[[_match_from_dict(m) for m in round_] for round_ in data["rounds"]],
        current_match_index=data["current_match_index"],
    )


def _game_to_dict(game: Game) -> dict:
    return {
        "board_size": game.board_size,
        "skip_limit": game.skip_limit,
        "prize_enabled": game.prize_enabled,
        "walls_enabled": game.walls_enabled,
        "wall_edges": _wall_edges_to_list(game.board.wall_edges),
        "obstacles_enabled": game.obstacles_enabled,
        "obstacle_cells": [list(cell) for cell in game.board.obstacle_cells],
        "pitfall_enabled": game.pitfall_enabled,
        "steal_enabled": game.steal_enabled,
        "special_cell_points": game.special_cell_points,
        "special_cells": _special_cells_to_list(game.board.special_cells),
        "wildcard_enabled": game.wildcard_enabled,
        "self_enclosed_penalty_enabled": game.self_enclosed_penalty_enabled,
        "reroll_enabled": game.reroll_enabled,
        "comeback_nudge_enabled": game.comeback_nudge_enabled,
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
                "special_captures": {
                    kind.value: count for kind, count in player.special_captures.items()
                },
                "rerolls_used": player.rerolls_used,
                "comeback_nudge_granted": player.comeback_nudge_granted,
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


def to_dict(game: Game, series: Series | None = None, tournament: Bracket | None = None) -> dict:
    return {
        "version": SAVE_FORMAT_VERSION,
        "series": _series_to_dict(series) if series is not None else None,
        "tournament": _bracket_to_dict(tournament) if tournament is not None else None,
        **_game_to_dict(game),
    }


def _game_from_dict(data: dict) -> Game:
    game = Game(
        board_size=data["board_size"],
        skip_limit=data["skip_limit"],
        prize_enabled=data.get("prize_enabled", False),
        walls_enabled=data.get("walls_enabled", False),
        obstacles_enabled=data.get("obstacles_enabled", False),
        pitfall_enabled=data.get("pitfall_enabled", False),
        steal_enabled=data.get("steal_enabled", False),
        special_cell_points=data.get("special_cell_points", {}),
        wildcard_enabled=data.get("wildcard_enabled", False),
        self_enclosed_penalty_enabled=data.get("self_enclosed_penalty_enabled", False),
        reroll_enabled=data.get("reroll_enabled", False),
        comeback_nudge_enabled=data.get("comeback_nudge_enabled", False),
    )
    if data.get("special_cells") is not None:
        game.board.special_cells = _special_cells_from_list(data["special_cells"])
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
        player.special_captures = {
            CellKind(kind): count for kind, count in player_data.get("special_captures", {}).items()
        }
        player.rerolls_used = player_data.get("rerolls_used", 0)
        player.comeback_nudge_granted = player_data.get("comeback_nudge_granted", False)
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

    return game


def from_dict(data: dict) -> tuple[Game, Series | None]:
    game = _game_from_dict(data)
    series_data = data.get("series")
    series = _series_from_dict(series_data) if series_data is not None else None
    return game, series


def save_game(
    game: Game,
    series: Series | None = None,
    tournament: Bracket | None = None,
    path: Path = DEFAULT_SAVE_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(to_dict(game, series, tournament)))
    os.replace(tmp_path, path)


def load_game(path: Path = DEFAULT_SAVE_PATH) -> tuple[Game, Series | None] | None:
    result = load_all(path)
    return None if result is None else (result[0], result[1])


def load_all(path: Path = DEFAULT_SAVE_PATH) -> tuple[Game, Series | None, Bracket | None] | None:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("version") != SAVE_FORMAT_VERSION:
        return None
    try:
        game, series = from_dict(data)
        tournament_data = data.get("tournament")
        tournament = _bracket_from_dict(tournament_data) if tournament_data is not None else None
    except (KeyError, TypeError, ValueError):
        return None
    return game, series, tournament


def has_save(path: Path = DEFAULT_SAVE_PATH) -> bool:
    return path.exists() and path.is_file()


def delete_save(path: Path = DEFAULT_SAVE_PATH) -> None:
    path.unlink(missing_ok=True)


def has_game_in_progress(game: Game | None) -> bool:
    return game is not None and game.state != TurnState.GAME_OVER and bool(game.history)


def should_save_on_exit(game: Game | None, series: Series | None, tournament: Bracket | None = None) -> bool:
    # A just-finished round (state == GAME_OVER) still needs saving while its
    # series isn't decided yet, otherwise quitting from the game-over screen
    # silently drops the series tally. Same reasoning extends one level up:
    # an in-progress tournament must survive a quit even between series. All
    # three still need an actual Game to serialize (e.g. a tournament quit
    # before its first match is begun has no Game yet) - nothing to save then.
    if game is None:
        return False
    return (
        has_game_in_progress(game)
        or (series is not None and not series.is_complete())
        or (tournament is not None and not tournament.is_complete())
    )
