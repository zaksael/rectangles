# Rectangles

A two-player pen-and-paper dice game, implemented as a Python/Pygame desktop app.

Two players share one grid board and grow their territory inward from
opposite corners by rolling dice and placing rectangles. Whoever covers more
area when the game ends wins.

## Rules

- The board is a shared 12×12 grid. Player 1 grows inward from the **top-left**
  corner; Player 2 grows inward from the **bottom-right** corner.
- Players alternate turns, starting with Player 1. On your turn, roll two
  six-sided dice — the two numbers become the width and height of a rectangle
  (rotatable, so a 2-and-5 roll can be placed as 2×5 or 5×2).
- Your first piece must be anchored exactly at your own starting corner.
  Every piece after that must be placed edge-adjacent to a piece you already
  own — touching only your opponent's territory doesn't count.
- If a roll can't legally be placed anywhere (in either orientation), your
  turn is skipped.
- The game ends when either:
  - neither player has any legal placement left anywhere on the board, or
  - one player is skipped several turns in a row (3 by default).
- Whoever has placed the most total area wins; equal areas is a tie.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management

## Setup

```bash
uv sync
```

## Play

```bash
uv run python main.py
```

- **Roll Dice** to get a piece for your turn.
- Hover over the board to preview placement, then click a highlighted (green)
  cell to place the piece.
- Rotate the piece with the `R` key, right-click, or the **Rotate** button.
- Click **Continue** to proceed after a skipped turn.
- Click **New Game** at any time to reset the board.

## Tests

```bash
uv run pytest
```

## Project structure

```
rectangles/
├── models.py     # Rectangle, Player
├── board.py      # grid + placement legality
├── game.py       # turn state machine, scoring, game-over rules
└── ui/           # Pygame rendering and input (all Pygame code lives here)
```

The rules engine (`models.py`, `board.py`, `game.py`) has no dependency on
Pygame, so it's fully unit-testable headlessly — see `tests/`.
