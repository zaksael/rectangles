from __future__ import annotations

from typing import Callable

from .constants import PLAYER_1, PLAYER_2
from .game import Game
from .models import Player, Rectangle

_Candidate = tuple[tuple[int, int], int, int]


def _opponent(game: Game) -> Player:
    other_id = PLAYER_2 if game.current_player_id == PLAYER_1 else PLAYER_1
    return game.players[other_id]


def _pick_best(
    game: Game,
    candidates: list[_Candidate],
    score: Callable[[_Candidate], int],
) -> _Candidate:
    scored = [(score(c), c) for c in candidates]
    best_score = max(s for s, _ in scored)
    best = [c for s, c in scored if s == best_score]
    return best[0] if len(best) == 1 else best[game.rng.randint(0, len(best) - 1)]


def _candidate_cells(candidate: _Candidate) -> set[tuple[int, int]]:
    top_left, w, h = candidate
    return set(Rectangle(top_left, w, h, 0).cells())


def flag_score(candidate: _Candidate, flag_cells: frozenset[tuple[int, int]]) -> int:
    return len(_candidate_cells(candidate) & flag_cells)


def blocking_score(candidate: _Candidate, opponent_frontier: set[tuple[int, int]]) -> int:
    return len(_candidate_cells(candidate) & opponent_frontier)


def choose_placement(game: Game, difficulty: str = "Basic") -> _Candidate:
    candidates = sorted(
        (top_left, w, h)
        for (w, h), top_lefts in game.legal_cache.items()
        for top_left in top_lefts
    )

    if difficulty == "Basic":
        return candidates[game.rng.randint(0, len(candidates) - 1)]

    if difficulty == "Greedy":
        flag_cells = game.board.flag_cells
        return _pick_best(game, candidates, lambda c: flag_score(c, flag_cells))

    if difficulty == "Blocking":
        opponent_frontier = game.board.frontier(_opponent(game))
        return _pick_best(game, candidates, lambda c: blocking_score(c, opponent_frontier))

    raise ValueError(f"Unknown bot difficulty: {difficulty}")
