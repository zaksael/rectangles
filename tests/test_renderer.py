import os

import pygame
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from rectangles.constants import PLAYER_1, PLAYER_2
from rectangles.game import Game, GameOverReason, TurnState
from rectangles.models import Rectangle, TurnRecord
from rectangles.series import Series
from rectangles.ui import layout
from rectangles.ui.renderer import Renderer
from rectangles.ui.state import ConfirmAction, Screen, UIState


class ScriptedRandom:
    def __init__(self, values):
        self._values = list(values)

    def randint(self, a, b):
        return self._values.pop(0)


def _finished_game(board_size, p1_area, p2_area):
    game = Game(board_size=board_size)
    if p1_area:
        game.board.place(game.players[PLAYER_1], (0, 0), p1_area, 1)
    if p2_area:
        game.board.place(game.players[PLAYER_2], (0, 0), p2_area, 1)
    return game


@pytest.fixture(scope="module")
def renderer():
    pygame.init()
    screen = pygame.display.set_mode((100, 100))
    return Renderer(screen)


def test_draw_settings_screen_smoke(renderer):
    renderer.draw(None, UIState(screen=Screen.SETTINGS))


def test_draw_awaiting_roll_smoke(renderer):
    game = Game(board_size=6)
    renderer.draw(game, UIState(screen=Screen.PLAYING))


@pytest.mark.parametrize("hover_legal", [True, False])
def test_draw_choosing_placement_smoke(renderer, hover_legal):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    ui_state = UIState(
        screen=Screen.PLAYING, current_dims=(2, 3), hover_top_left=(0, 0), hover_legal=hover_legal
    )
    renderer.draw(game, ui_state)


def test_draw_skipped_smoke(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_flag_conquest_smoke(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([0, 6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag, leaves 2 uncaptured
    if not game.check_game_over():
        game.end_turn()
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_walls_smoke(renderer):
    game = Game(board_size=11, walls_enabled=True)
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_obstacles_smoke(renderer):
    game = Game(board_size=11, obstacles_enabled=True)
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_self_enclosed_penalty_smoke(renderer):
    game = Game(board_size=11, self_enclosed_penalty_enabled=True)
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_choosing_wildcard_smoke(renderer):
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([3, 3, 0]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_choosing_placement_with_reroll_smoke(renderer):
    game = Game(board_size=6, reroll_enabled=True, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_PLACEMENT
    renderer.draw(game, UIState(screen=Screen.PLAYING, current_dims=(2, 3)))


def test_draw_skipped_with_reroll_smoke(renderer):
    game = Game(board_size=2, reroll_enabled=True, rng=ScriptedRandom([6, 6]))
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_choosing_wildcard_with_reroll_smoke(renderer):
    game = Game(board_size=6, wildcard_enabled=True, reroll_enabled=True, rng=ScriptedRandom([3, 3, 0]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_last_move_highlight_smoke(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    if not game.check_game_over():
        game.end_turn()
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_button_hover_sets_hand_cursor_flag(renderer):
    rect = pygame.Rect(10, 10, 20, 20)
    renderer._mouse_pos = rect.center
    renderer._hand_cursor = False
    renderer._button(rect, "Test")
    assert renderer._hand_cursor is True


def test_button_hover_flag_untouched_away_from_the_button(renderer):
    rect = pygame.Rect(10, 10, 20, 20)
    renderer._mouse_pos = (0, 0)
    renderer._hand_cursor = False
    renderer._button(rect, "Test")
    assert renderer._hand_cursor is False


def test_button_hover_ignored_when_disabled(renderer):
    rect = pygame.Rect(10, 10, 20, 20)
    renderer._mouse_pos = rect.center
    renderer._hand_cursor = False
    renderer._button(rect, "Test", enabled=False)
    assert renderer._hand_cursor is False


def test_last_placed_rect_none_before_any_history(renderer):
    game = Game(board_size=6)
    assert renderer._last_placed_rect(game) is None


def test_last_placed_rect_ignores_a_trailing_skip(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([2, 2, 6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()  # (6, 6) is too big for a 4x4 board regardless of state: guaranteed skip
    assert game.state == TurnState.SKIPPED

    last_placed = renderer._last_placed_rect(game)
    assert (last_placed.top_left, last_placed.width, last_placed.height) == ((0, 0), 2, 2)


def test_captured_flag_cells_none_without_flag_conquest(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    assert renderer._captured_flag_cells(game) == frozenset()


def test_captured_flag_cells_on_the_last_placement(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([0, 6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag (5, 5)
    assert renderer._captured_flag_cells(game) == frozenset({(5, 5)})


def test_captured_flag_cells_ignores_earlier_placements(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([0, 6, 6, 4, 4]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag (5, 5)
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((7, 7), 4, 4) is True  # P2's start-corner anchor; no flag in this footprint
    assert renderer._captured_flag_cells(game) == frozenset()


def test_last_placed_rect_upto_ignores_later_placements(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True

    upto_first = renderer._last_placed_rect(game, upto=1)
    assert (upto_first.top_left, upto_first.width, upto_first.height) == ((0, 0), 2, 2)


def test_captured_flag_cells_upto_ignores_later_placements(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([0, 6, 6, 4, 4]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # captures the center flag (5, 5)
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((7, 7), 4, 4) is True

    assert renderer._captured_flag_cells(game, upto=1) == frozenset({(5, 5)})
    assert renderer._captured_flag_cells(game, upto=2) == frozenset()


def test_placed_upto_returns_rects_in_history_order(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True

    assert renderer._placed_upto(game, 0) == []
    first = renderer._placed_upto(game, 1)
    assert [(r.top_left, r.width, r.height) for r in first] == [((0, 0), 2, 2)]
    both = renderer._placed_upto(game, 2)
    assert [(r.top_left, r.width, r.height) for r in both] == [((0, 0), 2, 2), ((3, 3), 3, 3)]


def test_new_scratch_board_seeds_real_start_corners(renderer):
    # Regression: scratch players used to be seeded with a hardcoded (0, 0)
    # start_corner, correct for Player 1 but wrong for Player 2 - harmless
    # while nothing called legal_top_lefts (which reads start_corner) on a
    # scratch board, but silently wrong for anything that does.
    game = Game(board_size=6)
    _, scratch = renderer._new_scratch_board(game)
    assert scratch[PLAYER_1].start_corner == game.players[PLAYER_1].start_corner == (0, 0)
    assert scratch[PLAYER_2].start_corner == game.players[PLAYER_2].start_corner == (5, 5)


def test_replay_stats_uses_historical_not_live_has_moved(renderer):
    # Regression: potential_area/flag_points read `has_moved` off the *live*
    # Player object, which is already True for Player 2 by the time both
    # players have moved - even at step 1, where Player 2 genuinely hasn't
    # placed anything yet historically. That wrongly skipped the
    # start-corner seeding branch and silently zeroed their potential area.
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True  # Player 2 now has_moved live

    stats = renderer._replay_stats(game, 1)  # only Player 1 has moved at this step
    assert stats[PLAYER_2]["potential_area"] > 0


def test_replay_stats_accumulates_area_and_flags(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([0, 6, 6, 4, 4]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # 36 area, captures the center flag (5, 5)
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((7, 7), 4, 4) is True  # 16 area, no flag in this footprint

    stats = renderer._replay_stats(game, 2)
    assert stats[PLAYER_1]["area"] == 36
    assert stats[PLAYER_1]["flags"] == 1
    assert stats[PLAYER_2]["area"] == 16
    assert stats[PLAYER_2]["flags"] == 0

    partial = renderer._replay_stats(game, 1)
    assert partial[PLAYER_1]["area"] == 36
    assert partial[PLAYER_1]["flags"] == 1
    assert partial[PLAYER_2]["area"] == 0
    assert partial[PLAYER_2]["flags"] == 0


def test_replay_stats_includes_potential_area_and_flag_points(renderer):
    game = Game(board_size=6, flag_conquest_enabled=True, flag_bonus_points=5, rng=ScriptedRandom([2, 2]))
    game.board.flag_cells = frozenset({(5, 5)})
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True  # 4 area, no flag captured
    if not game.check_game_over():
        game.end_turn()

    stats = renderer._replay_stats(game, 1)
    reachable = game.board.reachable_empty_cells(game.players[PLAYER_1])
    assert stats[PLAYER_1]["potential_area"] == len(reachable)
    assert stats[PLAYER_1]["potential_flag_points"] == 5  # the one reachable, uncaptured flag


def test_score_history_accumulates_scores_per_step(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, flag_bonus_points=5, rng=ScriptedRandom([0, 6, 6, 4, 4]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True  # 36 area, captures the center flag (5, 5)
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((7, 7), 4, 4) is True  # 16 area, no flag in this footprint

    history = renderer._score_history(game)
    assert history[PLAYER_1] == [0, 36 + 5, 36 + 5]
    assert history[PLAYER_2] == [0, 0, 16]


def test_wrap_text_splits_long_captions_to_fit_the_panel(renderer):
    # Regression: the replay caption for a wildcard placement ("Player 1
    # placed 6x5 (wildcard: rolled 5,5) at (0,0)") used to be drawn
    # unwrapped and ran off the panel/canvas edge entirely.
    caption = "Player 1 placed 6x5 (wildcard: rolled 5,5) at (0,0)"
    max_width = layout.PANEL_CONTENT_WIDTH

    lines = renderer._wrap_text(caption, renderer.font, max_width)

    assert len(lines) > 1
    assert " ".join(lines) == caption
    assert all(renderer.font.size(line)[0] <= max_width for line in lines)


def test_score_history_applies_self_enclosed_penalty_when_ring_completes(renderer):
    # Same ring-around-(2,2) layout as
    # test_board.py::test_self_enclosed_cell_counts_credits_hole_bordered_by_one_player_only,
    # fabricated directly into game.history (same technique test_input.py uses for game.history)
    # rather than played out through real turns, since _score_history only reads history/board.place.
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    game.history = [
        TurnRecord(player_id=PLAYER_1, roll=(1, 1), placed=Rectangle((1, 2), 1, 1, PLAYER_1)),
        TurnRecord(player_id=PLAYER_2, roll=(1, 1), placed=Rectangle((5, 5), 1, 1, PLAYER_2)),
        TurnRecord(player_id=PLAYER_1, roll=(1, 1), placed=Rectangle((3, 2), 1, 1, PLAYER_1)),
        TurnRecord(player_id=PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
        TurnRecord(player_id=PLAYER_1, roll=(1, 1), placed=Rectangle((2, 3), 1, 1, PLAYER_1)),
    ]

    history = renderer._score_history(game)
    assert history[PLAYER_1][4] == 3  # 3 of 4 ring cells placed, ring not yet closed
    assert history[PLAYER_1][5] == 4 - 1  # 4th ring cell closes it, encloses (2, 2)


def test_turn_analysis_empty_at_step_zero(renderer):
    game = Game(board_size=6)
    assert renderer._turn_analyses(game).get(0, []) == []


def test_turn_analysis_empty_for_a_skip(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty
    game.roll_dice()
    assert game.state == TurnState.SKIPPED

    assert renderer._turn_analyses(game).get(1, []) == []


def test_turn_analysis_flags_a_missed_flag_capture(renderer):
    # P1's first-ever move: legal_top_lefts collapses to one top_left per
    # orientation (anchored at the start corner), so the two candidates are
    # just the (1,4)/(4,1) orientation swap. The chosen 1x4 strip down
    # column 0 scores 0 against the flag at (0,3); the unchosen 4x1 strip
    # along row 0 scores 1.
    game = Game(board_size=6, flag_conquest_enabled=True)
    game.board.flag_cells = frozenset({(0, 3)})
    game.history = [TurnRecord(PLAYER_1, roll=(1, 4), placed=Rectangle((0, 0), 1, 4, PLAYER_1))]

    assert renderer._turn_analyses(game)[1] == [("missed flag capture (+1 available)", ((0, 0), 4, 1))]


def test_turn_analysis_flags_a_missed_denial(renderer):
    # Same layout as test_bot.py::test_choose_placement_blocking_prefers_denying_opponent_frontier
    # ((2, 3) is the one frontier cell that denies P2), but the historical
    # move picked (2, 1) instead.
    game = Game(board_size=6)
    game.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((2, 4), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
    ]

    assert renderer._turn_analyses(game)[3] == [("missed denial (+1 cells available)", ((2, 3), 1, 1))]


def test_turn_analysis_flags_a_self_created_enclosure(renderer):
    # Same ring-around-(2,2) layout as
    # test_score_history_applies_self_enclosed_penalty_when_ring_completes -
    # the final placement at (2, 3) is the one that closes the ring.
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    game.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((1, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((5, 5), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((3, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 3), 1, 1, PLAYER_1)),
    ]

    assert renderer._turn_analyses(game)[5] == [("created a 1-cell self-enclosed hole", None)]


def test_turn_analysis_flags_a_suboptimal_wildcard_pick(renderer):
    # P1's first-ever move, doubles (2,2) wildcard-edited down to a 1
    # (final roll (2,1)). Flag at (0,3): picking 4 instead (fixed die 2
    # stays, wildcard becomes 4) reaches it via a 4x2 placement; the chosen
    # value 1 can't reach col 3 at all. Neither player has moved yet, so
    # denial contributes 0 uniformly and doesn't affect which value wins.
    game = Game(board_size=6, flag_conquest_enabled=True, wildcard_enabled=True)
    game.board.flag_cells = frozenset({(0, 3)})
    game.history = [
        TurnRecord(
            PLAYER_1, roll=(2, 1), placed=Rectangle((0, 0), 1, 2, PLAYER_1), wildcard_original_roll=(2, 2)
        )
    ]

    assert renderer._turn_analyses(game)[1] == [
        ("suboptimal wildcard pick (rolling 4 instead would score +1)", ((0, 0), 4, 2))
    ]


def test_turn_analysis_no_note_when_wildcard_pick_already_optimal(renderer):
    # Same layout, but the wildcard was resolved to 4 (the best value) -
    # nothing to flag.
    game = Game(board_size=6, flag_conquest_enabled=True, wildcard_enabled=True)
    game.board.flag_cells = frozenset({(0, 3)})
    game.history = [
        TurnRecord(
            PLAYER_1, roll=(2, 4), placed=Rectangle((0, 0), 4, 2, PLAYER_1), wildcard_original_roll=(2, 2)
        )
    ]

    assert renderer._turn_analyses(game).get(1, []) == []


def test_turn_analysis_does_not_flag_a_forced_enclosure(renderer):
    # Every cell is already covered except a 1-wide pocket (2,2)-(2,3)
    # leading to an edge-adjacent 2x2 gap at (2,4) and P2's own corner cell.
    # board.legal_top_lefts for the closing 2x2 roll collapses to exactly
    # one position (every other candidate is blocked by already-P1 cells) -
    # sealing it does create a new self-enclosed hole, but since there was
    # no other legal move to make, it should not be flagged as a mistake.
    game = Game(board_size=6, self_enclosed_penalty_enabled=True)
    p2_cell = (5, 5)
    empties = {(2, 2), (2, 3), (2, 4), (2, 5), (3, 4), (3, 5)}
    history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((r, c), 1, 1, PLAYER_1))
        for r in range(6)
        for c in range(6)
        if (r, c) not in empties and (r, c) != p2_cell
    ]
    history.append(TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle(p2_cell, 1, 1, PLAYER_2)))
    history.append(TurnRecord(PLAYER_1, roll=(2, 2), placed=Rectangle((2, 4), 2, 2, PLAYER_1)))
    game.history = history

    assert renderer._turn_analyses(game).get(len(history), []) == []


def test_turn_analysis_anchors_second_player_candidates_at_real_start_corner(renderer):
    # Regression companion to test_new_scratch_board_seeds_real_start_corners:
    # P2's first-ever move is anchored at their real corner (5, 5), not a
    # hardcoded (0, 0) - if it were wrong, legal_top_lefts would come back
    # empty/mismatched and this move would (wrongly) look sub-optimal.
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True  # anchored at P2's real corner (5, 5)

    assert renderer._turn_analyses(game).get(2, []) == []


def test_turn_analyses_omits_clean_steps_from_the_dict(renderer):
    # Sparse dict shape: a step with no notes has no key at all (not an
    # empty list) - lets a plain `in` check double as the marker set for
    # the score chart.
    game = Game(board_size=6)
    game.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((2, 4), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
    ]

    assert set(renderer._turn_analyses(game).keys()) == {3}


def test_turn_analyses_caches_across_calls_for_the_same_game(renderer):
    game = Game(board_size=6)
    game.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((2, 4), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
    ]

    first = renderer._turn_analyses(game)
    second = renderer._turn_analyses(game)

    assert first is second


def test_turn_analyses_cache_busts_for_a_different_game(renderer):
    game_a = Game(board_size=6)
    game_a.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((2, 4), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
    ]
    game_b = Game(board_size=6)

    first = renderer._turn_analyses(game_a)
    second = renderer._turn_analyses(game_b)

    assert first is not second
    assert second == {}


def test_turn_analysis_note_text_is_unaffected_by_show_better_option(renderer, monkeypatch):
    # Revealing a better option is a purely visual board outline now (see
    # _draw_analysis_suggestions) - the note text itself never changes.
    game = Game(board_size=6, flag_conquest_enabled=True)
    game.board.flag_cells = frozenset({(0, 3)})
    game.history = [TurnRecord(PLAYER_1, roll=(1, 4), placed=Rectangle((0, 0), 1, 4, PLAYER_1))]

    drawn = []
    monkeypatch.setattr(renderer, "_text", lambda text, *a, **k: drawn.append(text))

    renderer._draw_turn_analysis(game, 1)
    assert drawn == ["! missed flag capture (+1 available)"]


def test_draw_replay_with_show_better_option_smoke(renderer):
    game = Game(
        board_size=6, flag_conquest_enabled=True, self_enclosed_penalty_enabled=True, rng=ScriptedRandom([2, 3])
    )
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    game.state = TurnState.GAME_OVER

    renderer.draw(game, UIState(screen=Screen.REPLAY, replay_step=1, replay_show_better_option=True))


def test_draw_replay_turn_analysis_smoke(renderer):
    game = Game(
        board_size=6, flag_conquest_enabled=True, self_enclosed_penalty_enabled=True, rng=ScriptedRandom([2, 3])
    )
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    game.state = TurnState.GAME_OVER

    renderer.draw(game, UIState(screen=Screen.REPLAY, replay_step=1))


def test_draw_replay_suboptimal_wildcard_pick_smoke(renderer):
    game = Game(board_size=6, flag_conquest_enabled=True, wildcard_enabled=True)
    game.board.flag_cells = frozenset({(0, 3)})
    game.history = [
        TurnRecord(
            PLAYER_1, roll=(2, 1), placed=Rectangle((0, 0), 1, 2, PLAYER_1), wildcard_original_roll=(2, 2)
        )
    ]
    game.state = TurnState.GAME_OVER

    renderer.draw(game, UIState(screen=Screen.REPLAY, replay_step=1, replay_show_better_option=True))


def test_draw_score_chart_with_a_flagged_turn_smoke(renderer):
    game = Game(board_size=6)
    game.history = [
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 2), 1, 1, PLAYER_1)),
        TurnRecord(PLAYER_2, roll=(1, 1), placed=Rectangle((2, 4), 1, 1, PLAYER_2)),
        TurnRecord(PLAYER_1, roll=(1, 1), placed=Rectangle((2, 1), 1, 1, PLAYER_1)),
    ]
    game.state = TurnState.GAME_OVER

    renderer.draw(game, UIState(screen=Screen.REPLAY, replay_step=3))


def test_format_turn_caption_placed_variant(renderer):
    game = Game(board_size=6, rng=ScriptedRandom([2, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 3) is True
    record = game.history[0]
    assert renderer._format_turn_caption(game, record) == "Player 1 placed 2x3"


def test_format_turn_caption_skip_variant(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty
    game.roll_dice()
    assert game.state == TurnState.SKIPPED
    record = game.history[0]
    assert renderer._format_turn_caption(game, record) == "Player 1 skipped (rolled 6,6)"


def test_format_turn_caption_wildcard_variant(renderer):
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([5, 5, 0]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD
    game.choose_wildcard_value(6)
    assert game.attempt_place((0, 0), 6, 5) is True
    record = game.history[0]
    assert renderer._format_turn_caption(game, record) == "Player 1 placed 6x5 (wildcard: rolled 5,5)"


@pytest.mark.parametrize("step", [0, 1, 2])
def test_draw_replay_smoke(renderer, step):
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True
    if not game.check_game_over():
        game.end_turn()
    game.state = TurnState.GAME_OVER

    renderer.draw(game, UIState(screen=Screen.REPLAY, replay_step=step))


@pytest.mark.parametrize("autoplay", [True, False])
def test_draw_replay_autoplay_controls_smoke(renderer, autoplay):
    game = Game(board_size=6, rng=ScriptedRandom([2, 2, 3, 3]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 2, 2) is True
    if not game.check_game_over():
        game.end_turn()
    game.roll_dice()
    assert game.attempt_place((3, 3), 3, 3) is True
    if not game.check_game_over():
        game.end_turn()
    game.state = TurnState.GAME_OVER

    for speed in ("Slow", "Normal", "Fast"):
        renderer.draw(
            game, UIState(screen=Screen.REPLAY, replay_step=1, replay_autoplay=autoplay, replay_speed=speed)
        )


def test_draw_replay_flag_conquest_smoke(renderer):
    # Leading 0 is consumed by the random flag pick during reset().
    game = Game(board_size=11, flag_conquest_enabled=True, rng=ScriptedRandom([0, 6, 6]))
    game.roll_dice()
    assert game.attempt_place((0, 0), 6, 6) is True
    game.state = TurnState.GAME_OVER

    renderer.draw(game, UIState(screen=Screen.REPLAY, replay_step=1))


def test_status_banner_message_none_on_a_normal_awaiting_roll(renderer):
    game = Game(board_size=6)
    assert renderer._status_banner_message(game) is None


def test_status_banner_message_on_choosing_wildcard(renderer):
    game = Game(board_size=6, wildcard_enabled=True, rng=ScriptedRandom([3, 3, 0]))
    game.roll_dice()
    assert game.state == TurnState.CHOOSING_WILDCARD

    assert renderer._status_banner_message(game) == "Wildcard roll! Player 1 may change one number"


def test_status_banner_message_on_skipped_turn(renderer):
    game = Game(board_size=4, rng=ScriptedRandom([6, 6]))
    p1 = game.players[PLAYER_1]
    game.board.place(p1, (0, 0), w=3, h=4)
    game.board.place(p1, (0, 3), w=1, h=3)  # only (3, 3) remains empty
    game.roll_dice()
    assert game.state == TurnState.SKIPPED

    assert renderer._status_banner_message(game) == "Player 1 skipped - no legal placement!"


@pytest.mark.parametrize(
    "reason",
    [
        GameOverReason.BOARD_FULL,
        GameOverReason.PLAYER_BLOCKED,
        GameOverReason.SKIP_LIMIT,
        GameOverReason.SURRENDER,
    ],
)
def test_draw_game_over_each_reason_smoke(renderer, reason):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = reason
    game.skipped_out_player_id = PLAYER_1
    game.blocked_player_id = PLAYER_2
    game.surrendered_player_id = PLAYER_1
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_game_over_tie_smoke(renderer):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    renderer.draw(game, UIState(screen=Screen.PLAYING))


def test_draw_panel_with_series_stats_smoke(renderer):
    game = Game(board_size=6, flag_conquest_enabled=True)
    series = Series(length=3, board_size=6, skip_limit=3, flag_conquest_enabled=True, flag_bonus_points=10)
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


def test_panel_series_rows_shows_everything_when_it_fits(renderer):
    series = Series(length=3, board_size=6, skip_limit=3)
    for _ in range(3):
        series.record_game(_finished_game(6, 1, 0))

    rows, hidden = renderer._panel_series_rows(series)

    assert hidden == 0
    assert [row[0] for row in rows] == ["1", "2", "3", "Total"]


def test_panel_series_rows_truncates_to_most_recent_plus_totals(renderer):
    from rectangles.ui import layout

    series = Series(length=5, board_size=6, skip_limit=3)
    for _ in range(5):
        series.record_game(_finished_game(6, 1, 0))

    rows, hidden = renderer._panel_series_rows(series)

    assert hidden == 3
    assert len(rows) == layout.PANEL_SERIES_MAX_ROWS - 2
    assert [row[0] for row in rows] == ["4", "5", "Total"]


def test_draw_panel_with_a_full_five_round_series_smoke(renderer):
    # The worst case that PANEL_SERIES_MAX_ROWS/MIN_WINDOW_HEIGHT are sized for:
    # a maxed-out history log alongside a full 5-round Flag Conquest series.
    game = Game(board_size=6, flag_conquest_enabled=True)
    series = Series(length=5, board_size=6, skip_limit=3, flag_conquest_enabled=True, flag_bonus_points=20)
    for _ in range(5):
        series.record_game(_finished_game(6, 1, 0))
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


def test_draw_game_over_with_series_in_progress_smoke(renderer):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


def test_draw_game_over_with_series_complete_smoke(renderer):
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    series = Series(length=3, board_size=6, skip_limit=3)
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))  # all 3 rounds played
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series)


@pytest.mark.parametrize("action", list(ConfirmAction))
def test_draw_confirm_dialog_each_action_smoke(renderer, action):
    game = Game(board_size=6)
    renderer.draw(game, UIState(screen=Screen.PLAYING, pending_confirmation=action))


def _bracket(n=4):
    from rectangles.tournament import Bracket, Participant

    participants = [Participant(name=f"Player {i + 1}") for i in range(n)]
    return Bracket(participants=participants, series_length=3, board_size=6, skip_limit=3)


def test_draw_settings_screen_with_tournament_bot_slots_smoke(renderer):
    ui_state = UIState(screen=Screen.SETTINGS, tournament_size=8)
    ui_state.tournament_slot_is_bot[1] = True
    renderer.draw(None, ui_state)


def test_draw_tournament_freshly_seeded_smoke(renderer):
    tournament = _bracket()
    renderer.draw(None, UIState(screen=Screen.TOURNAMENT), tournament=tournament)


def test_draw_tournament_mid_bracket_smoke(renderer):
    tournament = _bracket()
    match = tournament.current_match()
    match.series = tournament.new_series_for_current_match()
    match.winner = match.participant_a
    tournament.advance()
    renderer.draw(None, UIState(screen=Screen.TOURNAMENT), tournament=tournament)


def test_draw_tournament_complete_smoke(renderer):
    tournament = _bracket(n=4)
    for _ in range(3):
        match = tournament.current_match()
        match.series = tournament.new_series_for_current_match()
        match.winner = match.participant_a
        tournament.advance()
    assert tournament.is_complete()
    renderer.draw(None, UIState(screen=Screen.TOURNAMENT), tournament=tournament)


def test_draw_game_over_with_tournament_smoke(renderer):
    tournament = _bracket()
    match = tournament.current_match()
    series = tournament.new_series_for_current_match()
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    series.record_game(_finished_game(6, 1, 0))
    game = Game(board_size=6)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series, tournament=tournament)


def test_draw_panel_during_active_tiebreak_game_smoke(renderer):
    tournament = _bracket()
    match = tournament.current_match()
    series = tournament.new_series_for_current_match()
    series.record_game(_finished_game(6, 1, 1))
    series.record_game(_finished_game(6, 1, 1))
    series.record_game(_finished_game(6, 1, 1))  # tied series
    tiebreak = Game(board_size=6)
    match.tiebreak_game = tiebreak
    renderer.draw(tiebreak, UIState(screen=Screen.PLAYING), series=series, tournament=tournament)


def test_draw_game_over_tiebreak_smoke(renderer):
    tournament = _bracket()
    match = tournament.current_match()
    series = tournament.new_series_for_current_match()
    series.record_game(_finished_game(6, 1, 1))
    series.record_game(_finished_game(6, 1, 1))
    series.record_game(_finished_game(6, 1, 1))  # tied series
    game = Game(board_size=6)
    game.board.place(game.players[PLAYER_1], (0, 0), 3, 1)
    game.state = TurnState.GAME_OVER
    game.game_over_reason = GameOverReason.BOARD_FULL
    match.tiebreak_game = game
    renderer.draw(game, UIState(screen=Screen.PLAYING), series=series, tournament=tournament)
