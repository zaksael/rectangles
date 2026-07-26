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
- Rolling doubles (both dice show the same number) can optionally earn you
  an immediate extra turn, whether or not that roll could be placed — this
  house rule is off by default and configurable before each match.
- The game ends when any of the following happens:
  - neither player has any legal placement left anywhere on the board,
  - one player becomes completely boxed in by the opponent's territory (no
    empty cell touches their own anymore) even if empty cells remain
    elsewhere on the board, or
  - one player is skipped several turns in a row (configurable before each
    match, 3 by default), or
  - one player surrenders, in which case the other player wins outright
    regardless of area covered so far.
- Otherwise, whoever has placed the most total score (area, plus any flag
  bonus points — see [Flag Conquest](#flag-conquest) below) wins; equal
  scores is a tie.

## Flag Conquest

An optional mode, off by default. When turned on, three flags are seeded on
the board: the two corners *not* used as a starting corner (upper-right and
bottom-left), plus the exact center cell — which is why board sizes are
always odd, so the center is a single, unambiguous cell. Whichever player's
placed piece happens to cover a flag captures it immediately, earning a
configurable number of bonus points (5/10/20, selectable on the settings
screen) added on top of their area. A single large piece can capture more
than one flag at once if it covers them both.

## Bot opponent

Turn on **vs Bot (P2)** on the settings screen to play solo: Player 2 rolls,
places a random legal piece (or continues past a forced skip), and ends its
turn on its own, with a short pause between actions. Off by default. Human
input for Player 2's controls is ignored while the bot is taking its turn.

## Series mode

Instead of a single game, you can play a 3-round or 5-round series against
the same opponent: board size, skip limit, and mode settings (including
Flag Conquest, if enabled) are locked in once for every round. Every
round's score (same rules as above) adds to each player's running series
total — a landslide round counts for more than a squeaker — so the whole
series is always played out, and the player with the higher cumulative
score at the end wins. Equal cumulative scores after all rounds is a
tied series.

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
(preset buttons), optionally toggle the doubles house rule,
[Flag Conquest](#flag-conquest) (and its bonus-points preset) or the
[bot opponent](#bot-opponent), then click **Start Game**/`Space` for a
single match, or pick a series length (3 or 5 rounds) and click
**Start Series** to play a match series against the same opponent (see
[Series mode](#series-mode) above). **Exit**/`Esc` quits. If you quit mid-match, a **Resume Game**/`R`
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
├── series.py       # N-round match series (cumulative score, next-round setup)
├── bot.py          # picks a legal placement for the bot opponent
├── persistence.py  # save/load a game (and series, if one is in progress)
└── ui/             # Pygame rendering and input (all Pygame code lives here)
```

The rules engine (`models.py`, `board.py`, `game.py`, `series.py`, `bot.py`)
has no dependency on Pygame, so it's fully unit-testable headlessly — see
`tests/`.
