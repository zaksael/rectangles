# Rectangles

A two-player pen-and-paper dice game, implemented as a Python/Pygame desktop app.

Two players share one grid board and grow their territory inward from
opposite corners by rolling dice and placing rectangles. Whoever covers more
area when the game ends wins.

## Rules

For a precise, implementation-agnostic reference covering every rule and
optional mode in full detail, see [docs/GAME_SPEC.md](docs/GAME_SPEC.md).

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
- Rolling doubles (both dice show the same number) triggers a
  [Wildcard Roll](#wildcard-roll), if that optional mode is on.
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
the board: the exact center cell — which is why board sizes are always odd,
so the center is a single, unambiguous cell — plus two more flags at a
random position each game, mirrored through the center so neither player
starts closer to one than the other. Whichever player's
placed piece happens to cover a flag captures it immediately, earning a
fixed bonus of 10 points added on top of their area. A single large piece can capture more
than one flag at once if it covers them both. A gold ring marks whichever
flag cell(s) your most recent placement captured, so a capture doesn't go
unnoticed.

## Walls

An optional mode, off by default. When turned on, several wall lines are
seeded on the board in mirrored pairs, each pair randomly placed and
oriented (horizontal or vertical) and kept clear of both starting corners —
barriers that sit *between* cells rather than cells themselves, so no board
area is ever sacrificed; every cell stays placeable. A piece simply can't be
built across a wall line, and a piece on one side doesn't count as touching
territory on the other, so the only way past one is to build around its
ends. Each pair's second segment is the exact mirror image of the first
through the board's center, so the obstacle is symmetric for both players
regardless of which corner they start from.

## Obstacles

An optional mode, off by default. When turned on, a handful of individual
cells are seeded on the board in mirrored pairs, randomly placed and kept
clear of both starting corners, Flag Conquest's flags, and Walls' lines.
Unlike Walls, an obstacle cell is unplaceable itself — no piece can ever
cover it, and it never counts as a legal move for either player. Shown on
the board as a solid dark square.

## Wildcard Roll

An optional mode, off by default. When turned on, every roll that comes up
doubles (both dice matching) becomes a wildcard roll. One of the
two just-rolled numbers (picked at random) becomes yours to change to any
value 1-6, or leave as rolled — the other number stays fixed. Once you
finalize your pick, the turn proceeds exactly like a normal roll, placing if
that pair fits or skipping if it doesn't (including toward the skip streak).
If no number you could pick would ever fit, the pick is skipped entirely and
the turn resolves straight to a skip — no pointless click through an
all-illegal picker.

## Enclosure Penalty

An optional mode, off by default. When turned on, any empty cell that's
fully surrounded by only *your own* territory docks you 1 point — a live
penalty, recomputed every frame from the current board, not a one-time or
permanent effect. Filling the hole back in (even partially, breaking the
enclosure) drops the penalty immediately. A gap bordered by both players,
by neither (walled off or [Obstacles](#obstacles)-bound), or that touches
the board's outer edge at all, is never penalized — the edge already does
part of the enclosing for free, so only a hole your own territory fully
closes off, with no help from the edge, counts. The live panel shows the
penalty separately from your score (e.g. "-3 enclosed") so it's never
silently baked into the total.

## Reroll

An optional mode, off by default. Each player gets 2 rerolls per game (not
per turn, not per series round) to discard their current roll — both
dice — and roll fresh instead of accepting it. Usable any time a roll is
pending and you haven't committed to it yet: while choosing where to place,
while picking a [Wildcard Roll](#wildcard-roll) value, or when a roll would
otherwise skip your turn. Each use costs exactly one charge, no matter which
of those three situations you're in. The button shows your remaining count,
e.g. "Reroll (1/2)", and disappears once you're out. The bot never uses its
rerolls — it's a human-only resource.

## Bot opponent

Turn on **vs Bot (P2)** on the settings screen to play solo: Player 2 rolls,
places a legal piece (or continues past a forced skip), and ends its turn on
its own, with a short pause between actions. Off by default. Human input for
Player 2's controls is ignored while the bot is taking its turn.

Once the bot is on, pick its difficulty:
- **Basic** — picks uniformly at random among its legal placements.
- **Greedy** — prefers a placement that captures a flag (see
  [Flag Conquest](#flag-conquest)); with Flag Conquest off, or when no
  candidate reaches a flag, it falls back to a random pick.
- **Blocking** — prefers a placement that covers cells in *your* frontier,
  denying you those spots; falls back to a random pick among equally
  denying (or non-denying) candidates.

## Series mode

Instead of a single game, you can play a 3-round or 5-round series against
the same opponent: board size, skip limit, and mode settings (including
Flag Conquest, Walls, Obstacles, Wildcard Roll, Enclosure Penalty, and Reroll, if enabled) are locked in once for every round. Who
goes first alternates each round (Player 1 starts round 1, Player 2 starts
round 2, and so on), regardless of who won the previous round. Every
round's score (same rules as above) adds to each player's running series
total — a landslide round counts for more than a squeaker — so the whole
series is always played out, and the player with the higher cumulative
score at the end wins. Equal cumulative scores after all rounds is a
tied series. Both the in-game panel and the between-rounds screen show a
round-by-round breakdown (each round's score, plus flag bonus points when
Flag Conquest is on) alongside series-wide totals.

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
(preset buttons), optionally toggle
[Flag Conquest](#flag-conquest), [Walls](#walls),
[Obstacles](#obstacles), [Wildcard Roll](#wildcard-roll),
[Enclosure Penalty](#enclosure-penalty), [Reroll](#reroll) (or click
**Turn All ON**/**Turn All OFF** to flip all six at once), or the
[bot opponent](#bot-opponent) (and its difficulty preset), then click **Start Game**/`Space` for a
single match, or pick a series length (3 or 5 rounds) and click
**Start Series** to play a match series against the same opponent (see
[Series mode](#series-mode) above). **Exit**/`Esc` quits. If you quit mid-match, a **Resume Game**/`R`
button appears next time so you can pick up where you left off (including
the series score, if one was in progress).

The window can be freely resized in any direction to fit your screen — the
whole UI (board, panel, settings screen) scales together to fill it, with
board cells always staying square; a window whose proportions don't match
adds a plain border on the narrow sides rather than stretching anything.
In-game, the side panel's own scrollable bits (the turn history, and the
series stats table during a series) are capped instead: each shows only its
most recent entries plus a note when there's more, so the panel always fits.

- **Roll Dice** (`D`) to get a piece for your turn.
- All cells where your rolled piece could legally go are highlighted green;
  hover over the board to preview exact placement (centered on your cursor),
  then click a highlighted cell to place the piece.
- The most recently placed piece is outlined in gold, so you can spot your
  opponent's last move at a glance.
- Rotate the piece with the **Rotate** button, `R`, or right-click.
- A roll with no legal placement skips your turn automatically after a brief
  pause; click **Continue**/`Space` to skip the wait immediately instead. A
  banner over the board calls out the skip, and another calls out a wildcard
  roll, so neither is easy to miss.
- A [Wildcard Roll](#wildcard-roll) turn shows both dice, with the editable
  one shown as a black `*` until you pick its value, plus a row of buttons
  (grayed out for any value that wouldn't have a legal placement) to choose
  its new value before placement continues.
- With [Reroll](#reroll) on and a charge left, a **Reroll** button appears
  alongside the normal action for that turn — next to **Rotate** while
  choosing placement, alongside the value buttons on a wildcard roll, or
  in place of the single **Continue** button on a skip (split into
  **Reroll**/**Skip**). A skip with a reroll available waits for your
  choice instead of auto-continuing.
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
- **Replay** the finished game turn-by-turn: step through the board with
  First/Prev/Next/Last (or the arrow/Home/End keys), seeing each turn's
  roll, placement, each player's running area/flags at that point, a
  score-history chart plotting both players' scores across the whole game,
  and — for the turn just taken — any flagged missed opportunities (a
  bigger flag capture, more opponent denial, or a self-enclosed hole the
  placement created) versus the best other legal option that roll. Hit
  **Play** to watch it advance automatically at your chosen Slow/Normal/Fast
  pace — it stops at the last step, and any manual navigation pauses it.
  **Back**/`Esc` returns to the summary screen.
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
├── constants.py    # tunable game/UI values (board sizes, limits, presets)
├── models.py       # Rectangle, Player, TurnRecord
├── board.py        # grid + placement legality
├── game.py         # turn state machine, scoring, game-over rules
├── series.py       # N-round match series (cumulative score, next-round setup)
├── bot.py          # picks a placement for the bot opponent (Basic/Greedy/Blocking)
├── persistence.py  # save/load a game (and series, if one is in progress)
└── ui/             # Pygame rendering and input (all Pygame code lives here)
```

The rules engine (`constants.py`, `models.py`, `board.py`, `game.py`,
`series.py`, `bot.py`) has no dependency on Pygame, so it's fully
unit-testable headlessly — see `tests/`.
