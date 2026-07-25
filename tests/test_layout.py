from rectangles.ui import layout


def test_cell_rect():
    rect = layout.cell_rect(2, 3)
    assert (rect.x, rect.y, rect.width, rect.height) == (3 * layout.CELL_PX, 2 * layout.CELL_PX, layout.CELL_PX, layout.CELL_PX)


def test_piece_rect():
    rect = layout.piece_rect((1, 2), w=3, h=2)
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
    assert layout.pixel_to_cell(x, y, board_size=layout.MAX_BOARD_SIZE) == (8, 8)
