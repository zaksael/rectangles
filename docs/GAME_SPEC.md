# Rectangles — Game Rules

This is an implementation-agnostic specification of the "Rectangles" dice
game: everything needed to build (or referee by hand, with pen and paper) a
correct copy of the game, independent of any particular codebase, language,
or engine. For how *this* repository implements these rules, see
[CLAUDE.md](../CLAUDE.md). For how to install, run, and play this specific
implementation (controls, screens, buttons), see the [README](../README.md).

## 1. Overview

Two players, Player 1 and Player 2, share one square grid board. Player 1
grows a territory of placed rectangular pieces inward from the board's
top-left corner; Player 2 grows inward from the bottom-right corner. Players
alternate turns, rolling two six-sided dice each turn to determine the size
of the next piece they must place. The match ends once neither player can
ever place again, one player is completely boxed in, one player has been
skipped too many turns in a row, or one player surrenders. Whoever has the
higher score at that point wins; equal scores is a tie.

## 2. Setup

- The board is an N×N grid of cells. N is agreed before the match (typical
  choices: 19, 23, or 27); N should be odd if Flag Conquest (§6.1) is in
  play, so the board has a single, unambiguous center cell.
- Player 1 is assigned the top-left corner as their starting corner; Player
  2 is assigned the bottom-right corner.
- Two standard six-sided dice are used.
- Before play begins, the following are fixed for the whole match: board
  size, the skip limit (§7), and whichever optional rules (§6) are in play,
  each with their own parameters (e.g. flag bonus point value).

## 3. Turn structure

On the active player's turn:

1. They roll both dice, getting two numbers *a* and *b* (each 1–6).
2. Those numbers define a piece: a rectangle *a* cells by *b* cells, which
   may be oriented either way — *a* wide by *b* tall, or *b* wide by *a*
   tall (the two orientations are identical when *a = b*, i.e. doubles).
3. If there is at least one legal position on the board for that piece, in
   either orientation (see §4), the player chooses one such position (and
   thereby an orientation) and places the piece there, claiming its cells.
4. If there is no legal position for the piece in either orientation, the
   turn is skipped instead — no piece is placed, and this counts toward
   that player's skip streak (§7).
5. Play passes to the other player.

Turns always alternate between the two players (Player 1 moves first).

## 4. Placement legality

A candidate piece — a given width and height, at a given board position —
may be placed if and only if all of the following hold:

1. It fits entirely within the board.
2. Every cell it would cover is currently unclaimed by either player.
3. If Walls (§6.2) is in play, it does not straddle a wall line.
4. **Anchoring**:
   - A player's *very first* placement of the match must include their own
     starting corner as one of the piece's own corners.
   - *Every later* placement must share at least one full cell edge with a
     cell the *same* player already owns (an edge blocked by a wall, if
     Walls is in play, never counts). Sharing only a corner, or touching
     only the *opponent's* territory, is never sufficient — an unclaimed
     gap, even a single cell wide, blocks expansion across it until it's
     filled from either side.

## 5. Scoring

- A player's base score is the total number of cells they've claimed —
  i.e. the combined area of every piece they've placed.
- If Flag Conquest is in play, each flag a player has captured (§6.1) adds
  a fixed bonus to their score on top of that area.
- Whoever has the higher score once the game ends (§8) wins; equal scores
  is a tie — except when the game ended by surrender (§9), in which case
  the surrendering player's opponent always wins outright, regardless of
  either player's score.

## 6. Optional rules

Each of these is chosen independently before a match begins, and stays
fixed for the whole match (and, in series play, for every round of it).

### 6.1 Flag Conquest

When enabled: three flag cells are marked on the board before play begins —
the two board corners that are *not* either player's starting corner, plus
the board's exact center cell. A flag cell behaves like any other empty
cell for placement purposes; whichever player's piece happens to cover it
captures it immediately (a single large enough piece can capture more than
one flag at once). Each captured flag permanently earns that player a fixed
bonus (agreed before the match, e.g. 5, 10, or 20 points) added to their
score; flags are never lost once captured.

### 6.2 Walls

When enabled: two short wall segments (each three cells long) are marked on
the board before play begins — one positioned near each player's own
starting corner, offset two rows from the board's center line, each the
exact mirror image of the other through the board's center. A wall sits
*between* two adjacent cells, not on a cell itself — no board area is ever
removed from play, every cell stays placeable. However, no piece may be
placed straddling a wall line, and two cells on opposite sides of a wall are
never considered edge-adjacent for the placement rule in §4 — the only way
past a wall is to build around one of its ends.

### 6.3 Wildcard roll

When enabled: every roll becomes a wildcard roll if either of two conditions
holds — a fixed 1-in-6 random chance, or the roll came up doubles (both dice
show the same number). When it triggers, one of the two
just-rolled numbers (chosen at random) becomes freely editable — before
anything else happens, the active player may change that one number to any
value 1-6, or leave it as rolled. The other number keeps its original value.
Once the player finalizes their choice, the turn proceeds exactly as usual
from the resulting pair: a legal placement is made if one exists for that
pair, otherwise the turn is skipped — including counting toward the skip
streak (§7).

## 7. Skip limit and being boxed in

- A player who is skipped several turns *in a row* — a limit agreed before
  the match (typically 2, 3, or 5) — is eliminated from further play; see
  §8. A player's skip streak resets to zero the moment they successfully
  place a piece; a skip suffered by the *other* player never affects it.
- Independent of the skip limit: once a player has placed at least one
  piece, if every cell touching their own territory ever becomes claimed
  (by either player) or walled off, that player can never place again — a
  1×1 piece is always a possible roll (since both dice always show at
  least 1), and it would need at least one such cell.

## 8. Game over

The match ends the moment any of the following becomes true, checked in
this priority order (the first that applies is the reason the game ended):

1. **Board settled** — neither player has any cell left touching their own
   territory; nothing further can be built by anyone.
2. **Boxed in** — one player, having placed at least one piece, has no cell
   left touching their territory, while the other player still does; that
   player is permanently unable to move again.
3. **Skipped out** — one player has been skipped their agreed skip limit's
   worth of turns in a row (§7).

Once the match ends this way, whoever has the higher score (§5) wins; a tie
is possible.

## 9. Surrender

At any point during their own turn, a player may concede the match outright
instead of playing on. Their opponent wins immediately and unconditionally,
regardless of the score at that moment.

## 10. Bot opponent difficulty

For single-player play against an automated opponent, three difficulty
levels may be offered:

- **Basic** — chooses uniformly at random among all of its legal placements
  for the current roll.
- **Greedy** — prefers whichever legal placement captures the most flags
  (relevant only when Flag Conquest is in play — with it off, or when no
  candidate reaches a flag, this behaves exactly like Basic); ties are
  broken randomly.
- **Blocking** — prefers whichever legal placement takes away the most
  currently-available cells from its opponent (i.e. cells the opponent
  could otherwise have used for at least a 1×1 piece); ties are broken
  randomly.

## 11. Series play

Instead of a single game, a match may instead be a fixed-length series
(e.g. best-of-3 or best-of-5 rounds) against the same opponent, with board
size, skip limit, and every optional-rule setting locked for every round.
Each round's score (§5) adds to that player's running series total — a
landslide round counts for more than a squeaker — and every round in the
series is always played out; there is no early clinch. Whoever has the
higher cumulative score once all rounds are complete wins the series;
equal cumulative totals is a tied series.

## 12. Saving and resuming

A match in progress (and, if one is underway, its enclosing series) may be
saved and resumed later exactly where it left off, with no loss of state.

## 13. Reference: typical match settings

| Setting | Typical choices | Default |
|---|---|---|
| Board size | 19×19, 23×23, 27×27 | 19×19 |
| Skip limit | 2, 3, 5 | 3 |
| Flag Conquest | on / off | off |
| Flag bonus points | 5, 10, 20 | 10 |
| Walls | on / off | off |
| Wildcard roll | on / off | off |
| Bot difficulty | Basic, Greedy, Blocking | Basic |
| Series length | 3 or 5 rounds | — |
| Dice | two six-sided | — |
