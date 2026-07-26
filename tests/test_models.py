from rectangles.models import Player, Rectangle, TurnRecord


def test_rectangle_area():
    rect = Rectangle(top_left=(0, 0), width=3, height=4, owner=1)
    assert rect.area == 12


def test_rectangle_bottom_right():
    rect = Rectangle(top_left=(2, 3), width=4, height=2, owner=1)
    assert rect.bottom_right == (3, 6)


def test_rectangle_cells():
    rect = Rectangle(top_left=(1, 1), width=2, height=2, owner=1)
    assert set(rect.cells()) == {(1, 1), (1, 2), (2, 1), (2, 2)}


def test_player_total_area_sums_pieces():
    player = Player(1, "Player 1", (0, 0))
    player.pieces.append(Rectangle(top_left=(0, 0), width=2, height=3, owner=1))  # area 6
    player.pieces.append(Rectangle(top_left=(2, 0), width=1, height=1, owner=1))  # area 1
    assert player.total_area == 7


def test_player_total_area_zero_with_no_pieces():
    player = Player(1, "Player 1", (0, 0))
    assert player.total_area == 0


def test_player_flags_captured_defaults_to_zero():
    player = Player(1, "Player 1", (0, 0))
    assert player.flags_captured == 0


def test_player_has_moved_reflects_pieces():
    player = Player(1, "Player 1", (0, 0))
    assert player.has_moved is False
    player.pieces.append(Rectangle(top_left=(0, 0), width=1, height=1, owner=1))
    assert player.has_moved is True


def test_turn_record_stores_skip_with_no_placement():
    record = TurnRecord(player_id=1, roll=(4, 5), placed=None)
    assert record.placed is None
    assert record.roll == (4, 5)


def test_turn_record_stores_placement():
    rect = Rectangle(top_left=(0, 0), width=2, height=2, owner=1)
    record = TurnRecord(player_id=1, roll=(2, 2), placed=rect)
    assert record.placed is rect
