from __future__ import annotations

from .game import Game


def choose_placement(game: Game) -> tuple[tuple[int, int], int, int]:
    candidates = sorted(
        (top_left, w, h)
        for (w, h), top_lefts in game.legal_cache.items()
        for top_left in top_lefts
    )
    return candidates[game.rng.randint(0, len(candidates) - 1)]
