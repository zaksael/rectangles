from __future__ import annotations

from typing import Callable, TypeVar

from .constants import DICE_MAX, DICE_MIN, PLAYER_1, PLAYER_2
from .game import Game, TurnState
from .models import Player, Rectangle

_Candidate = tuple[tuple[int, int], int, int]
_DimsToTopLefts = dict[tuple[int, int], set[tuple[int, int]]]
_T = TypeVar("_T")


def _opponent(game: Game) -> Player:
    other_id = PLAYER_2 if game.current_player_id == PLAYER_1 else PLAYER_1
    return game.players[other_id]


def _break_tie(game: Game, scored: list[tuple[int, _T]]) -> _T:
    best_score = max(s for s, _ in scored)
    best = [item for s, item in scored if s == best_score]
    return best[0] if len(best) == 1 else best[game.rng.randint(0, len(best) - 1)]


def _pick_best(
    game: Game,
    candidates: list[_Candidate],
    score: Callable[[_Candidate], int],
) -> _Candidate:
    return _break_tie(game, [(score(c), c) for c in candidates])


def _candidate_cells(candidate: _Candidate) -> set[tuple[int, int]]:
    top_left, w, h = candidate
    return set(Rectangle(top_left, w, h, 0).cells())


def flag_score(candidate: _Candidate, flag_cells: frozenset[tuple[int, int]]) -> int:
    return len(_candidate_cells(candidate) & flag_cells)


def blocking_score(candidate: _Candidate, opponent_frontier: set[tuple[int, int]]) -> int:
    return len(_candidate_cells(candidate) & opponent_frontier)


def _blocking_score_fn(game: Game) -> Callable[[_Candidate], int]:
    # Computed once here, not inside the returned lambda - board.frontier() is
    # a full grid scan, and the lambda gets called once per candidate.
    opponent_frontier = game.board.frontier(_opponent(game))
    return lambda c: blocking_score(c, opponent_frontier)


# Per-difficulty scoring function, shared by choose_placement, choose_wildcard_value,
# and should_reroll - a difficulty absent here (i.e. "Basic") gets no smart wildcard/
# reroll behavior, only uniform-random placement.
_SCORE_FNS: dict[str, Callable[[Game], Callable[[_Candidate], int]]] = {
    "Greedy": lambda game: (lambda c: flag_score(c, game.board.flag_cells)),
    "Blocking": _blocking_score_fn,
}


def _candidates_from_dims(dims_to_top_lefts: _DimsToTopLefts) -> list[_Candidate]:
    return sorted(
        (top_left, w, h) for (w, h), top_lefts in dims_to_top_lefts.items() for top_left in top_lefts
    )


def _best_score(candidates: list[_Candidate], score_fn: Callable[[_Candidate], int]) -> int:
    return max((score_fn(c) for c in candidates), default=0)


def _legal_wildcard_values(game: Game) -> list[int]:
    return [v for v in range(DICE_MIN, DICE_MAX + 1) if game.wildcard_value_is_legal(v)]


def choose_placement(game: Game, difficulty: str = "Basic") -> _Candidate:
    candidates = _candidates_from_dims(game.legal_cache)

    if difficulty not in _SCORE_FNS:
        return candidates[game.rng.randint(0, len(candidates) - 1)]

    score_fn = _SCORE_FNS[difficulty](game)
    if difficulty == "Greedy":
        # flag_score ties at 0 for every candidate whenever no flag is
        # reachable this turn (structurally every turn with Flag Conquest
        # off) - area can't break that tie, every candidate in one turn
        # already shares the same w*h, so fall back to blocking_score, the
        # only other differentiator, instead of a bare random pick.
        blocking_fn = _blocking_score_fn(game)
        return _break_tie(game, [((score_fn(c), blocking_fn(c)), c) for c in candidates])

    return _pick_best(game, candidates, score_fn)


def choose_wildcard_value(game: Game, difficulty: str = "Basic") -> int:
    if difficulty not in _SCORE_FNS:
        # Not filtered to legal values - matches existing Basic behavior, which
        # can occasionally pick an illegal value and force an unnecessary skip.
        return game.rng.randint(DICE_MIN, DICE_MAX)

    score_fn = _SCORE_FNS[difficulty](game)
    scored = []
    for v in _legal_wildcard_values(game):
        dims_to_top_lefts = game.legal_placements_for_value(v)
        best = _best_score(_candidates_from_dims(dims_to_top_lefts), score_fn)
        if difficulty == "Greedy":
            # Unlike choose_placement (every candidate in one turn shares one
            # w*h), different wildcard values give different piece sizes.
            # Greedy's flag_score ties at 0 whenever no value reaches a flag;
            # break that tie toward the larger piece instead of a bare
            # random pick.
            area = max((w * h for (w, h), top_lefts in dims_to_top_lefts.items() if top_lefts), default=0)
            scored.append(((best, area), v))
        else:
            scored.append((best, v))
    return _break_tie(game, scored)


def should_reroll(game: Game, difficulty: str) -> bool:
    if difficulty not in _SCORE_FNS or not game.can_reroll():
        return False

    if game.state == TurnState.SKIPPED:
        return True

    if difficulty == "Greedy" and not game.board.flag_cells:
        # flag_score is structurally 0 all game without a flag on the board -
        # a reroll can never score better, so a 0 here isn't a "bad roll"
        # signal the way it is for Blocking's turn-to-turn frontier target.
        return False

    score_fn = _SCORE_FNS[difficulty](game)
    if game.state == TurnState.CHOOSING_PLACEMENT:
        return _best_score(_candidates_from_dims(game.legal_cache), score_fn) == 0
    if game.state == TurnState.CHOOSING_WILDCARD:
        return max(
            _best_score(_candidates_from_dims(game.legal_placements_for_value(v)), score_fn)
            for v in _legal_wildcard_values(game)
        ) == 0
    return False
