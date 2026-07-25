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
- Rolling doubles (both dice show the same number) earns you an immediate
  extra turn, whether or not that roll could be placed.
- The game ends when any of the following happens:
  - neither player has any legal placement left anywhere on the board,
  - one player becomes completely boxed in by the opponent's territory (no
    empty cell touches their own anymore) even if empty cells remain
    elsewhere on the board, or
  - one player is skipped several turns in a row (configurable before each
    match, 3 by default), or
  - one player surrenders, in which case the other player wins outright
    regardless of area covered so far.
- Otherwise, whoever has placed the most total area wins; equal areas is a
  tie.

## Series mode

Instead of a single game, you can play a best-of-3 or best-of-5 series
against the same opponent: board size and skip limit are locked in once for
every round, and each round's winner (by area, same rules as above) earns one
series win. A tied round counts toward the games played but doesn't award
either side a point. The series ends as soon as one player reaches the
majority of wins (2 of 3, or 3 of 5) — it doesn't need to play out every
round — or, in the rare case of enough tied rounds, can itself end tied.

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
(preset buttons), then click **Start Game**/`Space` for a single match, or
pick a series length (best-of-3/5) and click **Start Series** to play a
match series against the same opponent (see [Series mode](#series-mode)
above). **Exit**/`Esc` quits. If you quit mid-match, a **Resume Game**/`R`
button appears next time so you can pick up where you left off (including
the series score, if one was in progress).

- **Roll Dice** (`D`) to get a piece for your turn.
- All cells where your rolled piece could legally go are highlighted green;
  hover over the board to preview exact placement, then click a highlighted
  cell to place the piece.
- Rotate the piece with the **Rotate** button, `R`, or right-click.
- **Continue** (`Space`) to proceed after a skipped turn.
- **New Game** (`N`) at any time during a match to return to the settings
  screen and start a fresh match, or **Exit** (`Esc`) to quit outright.
  Once you've placed at least one piece, either of these (and closing the
  window) asks for confirmation first, so you can't lose progress by
  accident.
- **Surrender** (`S`) to concede the match immediately — your opponent
  wins regardless of the current area tally. Always asks for confirmation
  first, even before you've placed a single piece.
- When the game ends, a summary screen shows the winner (or tie), final
  scores, and the reason the game ended, with **New Game**/`N` and
  **Exit**/`Esc` buttons. During a series, that button reads **Next Game**
  and starts the next round instead, until the series itself is decided.
- The side panel keeps a running **History** log of every placement and
  skip, most recent first; scroll the mouse wheel over it to see older
  entries once a match runs past the visible rows.

## Tests

```bash
uv run pytest
```

## Project structure

```
rectangles/
├── models.py       # Rectangle, Player, TurnRecord
├── board.py        # grid + placement legality
├── game.py         # turn state machine, scoring, game-over rules
├── series.py       # best-of-N match series (win tracking, next-round setup)
├── persistence.py  # save/load a game (and series, if one is in progress)
└── ui/             # Pygame rendering and input (all Pygame code lives here)
```

The rules engine (`models.py`, `board.py`, `game.py`, `series.py`) has no
dependency on Pygame, so it's fully unit-testable headlessly — see `tests/`.
