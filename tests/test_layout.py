from rectangles.ui import layout


def test_cell_rect():
    rect = layout.cell_rect(2, 3, board_size=8)
    assert (rect.x, rect.y, rect.width, rect.height) == (3 * layout.CELL_PX, 2 * layout.CELL_PX, layout.CELL_PX, layout.CELL_PX)


def test_piece_rect():
    rect = layout.piece_rect((1, 2), w=3, h=2, board_size=8)
    assert (rect.x, rect.y, rect.width, rect.height) == (
        2 * layout.CELL_PX,
        1 * layout.CELL_PX,
        3 * layout.CELL_PX,
        2 * layout.CELL_PX,
    )


def test_board_rect():
    rect = layout.board_rect(8)
    assert (rect.x, rect.y, rect.width, rect.height) == (0, 0, 8 * layout.CELL_PX, 8 * layout.CELL_PX)


def test_pixel_to_cell_inside_board():
    assert layout.pixel_to_cell(layout.CELL_PX + 1, layout.CELL_PX + 1, board_size=8) == (1, 1)


def test_pixel_to_cell_outside_window_returns_none():
    assert layout.pixel_to_cell(-1, 0, board_size=8) is None
    assert layout.pixel_to_cell(0, -1, board_size=8) is None


def test_pixel_to_cell_respects_smaller_board_size():
    # A point within the fixed max-size window but outside a smaller chosen
    # board's rect must not resolve to a cell (board.py's MAX_BOARD_SIZE note).
    x = y = 8 * layout.CELL_PX + 1  # just past an 8x8 board's edge
    assert layout.pixel_to_cell(x, y, board_size=8) is None
    assert layout.pixel_to_cell(x, y, board_size=layout.MAX_BOARD_SIZE) is not None


def test_cell_px_shrinks_to_fit_target_board_px():
    # A board whose natural footprint at the flat CELL_PX would exceed
    # TARGET_BOARD_PX shrinks its per-cell size to fit back within it.
    big_size = layout.TARGET_BOARD_PX // layout.CELL_PX + 1
    assert layout.cell_px(big_size) == layout.TARGET_BOARD_PX // big_size
    assert layout.cell_px(big_size) < layout.CELL_PX


def test_cell_px_stays_flat_for_presets_that_already_fit():
    for size in (11, 15, 19):
        assert layout.cell_px(size) == layout.CELL_PX


def test_game_over_buttons_are_three_distinct_non_overlapping_rects():
    new_game = layout.GAME_OVER_NEW_GAME_BUTTON_RECT
    replay = layout.GAME_OVER_REPLAY_BUTTON_RECT
    exit_rect = layout.GAME_OVER_EXIT_BUTTON_RECT
    rects = [new_game, replay, exit_rect]
    assert len(rects) == len(set((r.x, r.y) for r in rects))
    for a, b in ((new_game, replay), (replay, exit_rect)):
        assert not a.colliderect(b)
    assert new_game.y == replay.y == exit_rect.y


def test_replay_button_rects_returns_nine_non_overlapping_rects():
    rects = layout.REPLAY_BUTTON_RECTS
    assert set(rects.keys()) == {"first", "prev", "next", "last", "play", "Slow", "Normal", "Fast", "back"}
    ordered = [
        rects["first"],
        rects["prev"],
        rects["next"],
        rects["last"],
        rects["play"],
        rects["Slow"],
        rects["Normal"],
        rects["Fast"],
        rects["back"],
    ]
    for a, b in zip(ordered, ordered[1:]):
        assert not a.colliderect(b)
        assert a.right <= b.left


def test_compute_scale_fits_design_canvas_uniformly():
    scale, offset_x, offset_y = layout.compute_scale(layout.DESIGN_WIDTH * 2, layout.DESIGN_HEIGHT * 2)
    assert scale == 2.0
    assert (offset_x, offset_y) == (0, 0)


def test_compute_scale_letterboxes_mismatched_aspect_ratio():
    # Much wider than the design canvas at the same height - height is the
    # binding dimension, so extra width becomes pillarbox bars either side.
    scale, offset_x, offset_y = layout.compute_scale(layout.DESIGN_WIDTH * 4, layout.DESIGN_HEIGHT)
    assert scale == 1.0
    assert offset_x > 0
    assert offset_y == 0


def test_compute_scale_clamps_to_max():
    huge_scale, _, _ = layout.compute_scale(layout.DESIGN_WIDTH * 100, layout.DESIGN_HEIGHT * 100)
    assert huge_scale == layout._MAX_SCALE


def test_to_design_coords_round_trips_through_compute_scale():
    real_width, real_height = layout.DESIGN_WIDTH * 2, layout.DESIGN_HEIGHT * 2
    scale, offset_x, offset_y = layout.compute_scale(real_width, real_height)
    real_x, real_y = offset_x + 40 * scale, offset_y + 60 * scale
    assert layout.to_design_coords(real_x, real_y, real_width, real_height) == (40, 60)


def test_settings_action_row_y_grows_with_content_height():
    # Series shows an extra row (Series Length) that Single doesn't, and
    # Tournament shows more rows still (its own extra rows plus per-slot
    # rows), so each sits lower on screen than the last.
    assert layout.settings_action_row_y("Single", 4) < layout.settings_action_row_y("Series", 4)
    assert layout.settings_action_row_y("Series", 4) < layout.settings_action_row_y("Tournament", 4)


def test_settings_max_scroll_is_greatest_in_tournament_mode():
    # Tournament mode at its largest slot preset carries every other mode's
    # content plus its own per-slot rows, so it never scrolls less than
    # Single/Series - and dynamic slot sizing means it's the only mode/size
    # combination that still needs to scroll at all.
    assert layout.settings_max_scroll("Tournament", 8) >= layout.settings_max_scroll("Single", 4)
    assert layout.settings_max_scroll("Tournament", 8) >= layout.settings_max_scroll("Series", 4)
    assert layout.settings_max_scroll("Tournament", 8) > 0


def test_settings_content_height_max_covers_every_mode():
    for mode in ("Single", "Series", "Tournament"):
        for tournament_size in layout.TOURNAMENT_SIZE_PRESETS:
            assert layout.settings_content_height(mode, tournament_size) <= layout.SETTINGS_CONTENT_HEIGHT_MAX
