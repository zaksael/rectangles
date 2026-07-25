# Rectangles

A two-player pen-and-paper dice game, implemented as a Python/Pygame desktop app.

Two players share one grid board and grow their territory inward from
opposite corners by rolling dice and placing rectangles. Whoever covers more
area when the game ends wins.

## Rules

- The board is a shared grid (size configurable before each match). Player 1
  grows inward from the **top-left** corner; Player 2 grows inward from the
  **bottom-right** corner.
- Players alternate turns, starting with Player 1. On your turn, roll two
  six-sided dice — the two numbers become the width and height of a rectangle
  (rotatable, so a 2-and-5 roll can be placed as 2×5 or 5×2).
- Your first piece must be anchored exactly at your own starting corner.
  Every piece after that must be placed edge-adjacent to a piece you already
  own — touching only your opponent's territory doesn't count.
- If a roll can't legally be placed anywhere (in either orientation), your
  turn is skipped.
- The game ends when any of the following happens:
  - neither player has any legal placement left anywhere on the board,
  - one player becomes completely boxed in by the opponent's territory (no
    empty cell touches their own anymore) even if empty cells remain
    elsewhere on the board, or
  - one player is skipped several turns in a row (configurable before each
    match, 3 by default).
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

The app opens to a settings screen — pick a board size and skip limit
(preset buttons), then click **Start Game** (or **Exit**/`Esc` to quit).

- **Roll Dice** (`D`) to get a piece for your turn.
- All cells where your rolled piece could legally go are highlighted green;
  hover over the board to preview exact placement, then click a highlighted
  cell to place the piece.
- Rotate the piece with the **Rotate** button, `R`, or right-click.
- **Continue** (`Space`) to proceed after a skipped turn.
- **New Game** (`N`) at any time during a match to return to the settings
  screen and start a fresh match.
- When the game ends, a summary screen shows the winner (or tie), final
  scores, and the reason the game ended, with **New Game**/`N` and
  **Exit**/`Esc` buttons.
- The side panel keeps a running **History** log of every placement and
  skip, most recent first.

## Tests

```bash
uv run pytest
```

## Project structure

```
rectangles/
├── models.py     # Rectangle, Player, TurnRecord
├── board.py      # grid + placement legality
├── game.py       # turn state machine, scoring, game-over rules
└── ui/           # Pygame rendering and input (all Pygame code lives here)
```

The rules engine (`models.py`, `board.py`, `game.py`) has no dependency on
Pygame, so it's fully unit-testable headlessly — see `tests/`.
