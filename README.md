# Rectangles

A two-player pen-and-paper dice game, implemented as a Python rules engine and WebSocket server with a React
frontend that runs in the browser.

Two players share one grid board and grow their territory inward from
opposite corners by rolling dice and placing rectangles. Whoever covers more
area when the game ends wins.

## Index

- [Requirements](#requirements)
- [Setup](#setup)
- [Play](#play)
- [Accessibility](#accessibility)
- [Development](#development)
  - [Frontend development](#frontend-development)
- [Tests](#tests)
- [Rules](#rules)
- [House Rules](#house-rules)
  - [Prize](#prize)
  - [Walls](#walls)
  - [Obstacles](#obstacles)
  - [Pitfall](#pitfall)
  - [Steal](#steal)
  - [Wildcard Roll](#wildcard-roll)
  - [Enclosure Penalty](#enclosure-penalty)
  - [Reroll](#reroll)
  - [Comeback](#comeback)
- [Bot opponent](#bot-opponent)
- [Series mode](#series-mode)
- [Project structure](#project-structure)

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Node.js 22.12 or newer and npm, to build the frontend

## Setup

```bash
uv sync
cd frontend
npm install
npm run build
```

## Play

```bash
uv run python -m rectangles.server.app
```

Then open `http://127.0.0.1:8765/` (set `RECTANGLES_SERVER_HOST` and
`RECTANGLES_SERVER_PORT` to change the address). The server serves the built frontend from
`frontend/dist` and the game socket at `/ws`; without a build it serves only
`/ws`.

A game lives in its browser tab: the server keeps one game per connection, with no accounts, so
reloading or closing the tab ends it (the browser asks before leaving a game in progress).

The game opens on Mode Select. Pick the opponent (**Local 2P** or **Vs Bot** and
its difficulty), a board size and skip limit, how many games to play (1, 3 or
5, see [Series mode](#series-mode)), and which of the nine
[house rules](#house-rules) to switch on, then **Start Game**. Your last choices
are remembered, and **Reset to Defaults** appears once any differ.

Playing and Replay need a window at least 1320px wide; below that a "Widen the
Window" notice takes their place and the game waits where it was.

- **Roll** (`D`) to get a piece for your turn.
- Every cell where your rolled piece could legally go is highlighted; hover
  the board (or tap, then tap again to place) to preview the exact placement,
  centered on the pointer, and click to place the piece. The keyboard works
  too: arrows move the cursor, `N` / `Shift+N` jump to the next / previous
  legal spot, and `Enter` places.
- Rotate the piece with the **Rotate** button or `R`.
- A roll with no legal placement waits for you to press **Skip** (`S`).
- A [Wildcard Roll](#wildcard-roll) turn shows a row of value buttons (greyed
  out for any value without a legal placement) to choose the editable die's
  value before placement continues.
- With [Reroll](#reroll) on and a charge left, **Reroll** (`E`) discards the
  current roll for a fresh one, including alongside a forced skip.
- The side rail shows both scores with a row for each scoring rule that is
  on, each player's skip streak, a legend of the special cells, and the
  latest moves.
- **Menu** (`M`) shows the match settings and has **Resume** and
  **Surrender**; surrender always asks for confirmation first, and your
  opponent wins regardless of the area tally.
- When the game ends, a summary shows the winner (or tie), final scores, the
  score breakdown and the reason the game ended. **View Board** (`V`) looks at
  the final board with a slim result bar, **Replay** (`R`) steps through the
  game, and **New Game** (`N`) returns to Mode Select. During a series the
  button reads **Next Round** until the series itself is decided, then **Series
  Result**.
- **Replay** the finished game turn by turn: step with First/Prev/Next/Last
  (or the arrow, Home and End keys), seeing each turn's roll, placement and
  each player's score breakdown at that point, plus a score-history chart
  across the whole game (click or arrow along it to jump to a turn). For the
  turn just taken, a flag appears if the best other legal option that roll
  would have scored higher than what was actually played, showing the actual
  score against the best possible one (e.g. "scored 4 this turn (best
  possible: 14 — prize)") — or, when the difference is purely strategic
  denial rather than real points, the cells denied instead (e.g. "denied 1
  cell this turn (best possible: 5)"). Toggle **Show Better Option** to
  outline the better placement on the board. **Play** advances automatically
  at the Slow/Normal/Fast pace you pick; it stops at the last step, and any
  manual navigation pauses it. **Back**/`Esc` returns to the summary.

## Accessibility

- **Keyboard:** every control on Playing is reachable by keyboard. The board is a single tab stop on every
  turn and keeps focus between turns; the piece starts on the first legal spot when you focus it or a
  new placement begins.
- **Screen readers:** the turn status, each roll ("Player 1 rolled 2 and 1") and the piece's position with
  what it would sit on ("Row 5, column 7, 4 empty cells") are announced as they change. The board has a
  hidden summary of each player's pieces and cells, plus obstacles and walls.
- **Colour and touch:** the player colours and the illegal-placement colour were checked under red-green
  and blue-yellow colour blindness, and special cells are told apart by shape (`+`, `−`, `±`) as well as
  position. Touch screens get 44px controls, and dialogs are inset to clear a phone's notch and corners.

## Development

### Frontend development

Run the server in one terminal (`uv run python -m rectangles.server.app`) and
`npm run dev` in `frontend/` in another. The Vite dev server forwards `/ws` to
the server on port 8765; open the printed `localhost` URL to play. The server
accepts a WebSocket only from a page served from its own host and port, which
the Vite proxy preserves.

## Tests

```bash
uv run pytest                  # backend: engine and server
cd frontend
npm test                       # frontend (Vitest)
npm run lint
```

Coverage is about 99% on the backend and 97% on the frontend (measured with `pytest-cov` and
`@vitest/coverage-v8`, neither a project dependency).

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
    match, 5 by default), or
  - one player surrenders, in which case the other player wins outright
    regardless of area covered so far.
- Otherwise, whoever has placed the most total score (area, plus any prize
  bonus points — see [Prize](#prize) below) wins; equal
  scores is a tie.

## House Rules

Nine optional modes, toggled independently on the Mode Select screen before a
match begins. All nine start switched on the first time; after that your last
choice is kept.

### Prize

When turned on, four prize cells are seeded on
the board: two random positions each game, each mirrored through the
board's center so neither player starts closer to one than the other. Prizes
are kept clear of both starting corners and spread apart from each other,
so they never cluster together. Whichever player's
placed piece happens to cover a prize captures it immediately, earning a
fixed bonus of 10 points added on top of their area. A single large piece can capture more
than one prize at once if it covers them both. Shown on the board as a plus
mark, which disappears once a piece covers it; a ring around whichever
prize cell(s) your most recent placement captured makes sure a capture
doesn't go unnoticed.

### Walls

When turned on, several wall lines are
seeded on the board in mirrored pairs, each pair randomly placed and
oriented (horizontal or vertical), kept clear of both starting corners, and
spread apart from any other wall pair so they never cluster together —
barriers that sit *between* cells rather than cells themselves, so no board
area is ever sacrificed; every cell stays placeable. A piece simply can't be
built across a wall line, and a piece on one side doesn't count as touching
territory on the other, so the only way past one is to build around its
ends. Each pair's second segment is the exact mirror image of the first
through the board's center, so the obstacle is symmetric for both players
regardless of which corner they start from.

### Obstacles

When turned on, four individual
cells (two mirrored pairs) are seeded on the board in mirrored pairs, randomly placed and kept
clear of both starting corners, Prize's cells, Walls' lines, and
any other Obstacle pair, so they never cluster together.
Unlike Walls, an obstacle cell is unplaceable itself — no piece can ever
cover it, and it never counts as a legal move for either player. Shown on
the board as a solid dark square.

### Pitfall

When turned on, four pitfall cells are seeded
on the board as two mirrored pairs, randomly placed and kept clear of
both starting corners and every other special cell (Prize's cells,
Walls' lines, Obstacles), so they never overlap. Covering a pitfall docks the
capturer 10 points off their own score — the mirror image of Prize's
bonus, with no effect on the opponent. Scores aren't floored at 0, so
triggering enough pitfalls can push a player negative. Shown on the board as a
bar mark, which disappears once a piece covers it, and the score table keeps a
separate Pitfall row so it's never silently baked into the total.

### Steal

When turned on, two steal cells are seeded on
the board as a single mirrored pair, randomly placed and kept clear of both
starting corners and every other special cell (Prize's cells, Walls' lines,
Obstacles, Pitfall's cells), so they never overlap. Covering a steal cell is a
zero-sum transfer: you gain 10 points *and* your opponent loses 10, a 20-point
swing in the score gap for a single cell — higher stakes than Prize's pure
gain or Pitfall's pure loss. Scores aren't floored at 0, so being on the wrong
end of enough steals can push you negative. Shown on the board as a
plus-over-minus mark, which disappears once a piece covers it; the score table's
Steal row shows each player's net swing (+10 for the capturer, −10 for the
opponent) so it's never silently baked into the total.

### Wildcard Roll

When turned on, every roll that comes up
doubles (both dice matching) becomes a wildcard roll. One of the
two just-rolled numbers (picked at random) becomes yours to change to any
value 1-6, or leave as rolled — the other number stays fixed. Once you
finalize your pick, the turn proceeds exactly like a normal roll, placing if
that pair fits or skipping if it doesn't (including toward the skip streak).
If no number you could pick would ever fit, the pick is skipped entirely and
the turn resolves straight to a skip — no pointless click through an
all-illegal picker.

### Enclosure Penalty

When turned on, any empty cell that's
fully surrounded by only *your own* territory docks you 1 point — a live
penalty, recomputed after every move from the current board, not a one-time or
permanent effect. Filling the hole back in (even partially, breaking the
enclosure) drops the penalty immediately. A gap bordered by both players,
by neither (walled off or [Obstacles](#obstacles)-bound), or that touches
the board's outer edge at all, is never penalized — the edge already does
part of the enclosing for free, so only a hole your own territory fully
closes off, with no help from the edge, counts. The enclosed cells are hatched in your colour on the board, and the score
table keeps a separate Enclosure row so the penalty is never silently baked
into the total.

### Reroll

Each player gets 2 rerolls per game (not
per turn, not per series round) to discard their current roll — both
dice — and roll fresh instead of accepting it. Usable any time a roll is
pending and you haven't committed to it yet: while choosing where to place,
while picking a [Wildcard Roll](#wildcard-roll) value, or when a roll would
otherwise skip your turn. Each use costs exactly one charge, no matter which
of those three situations you're in. The score table's Rerolls row shows each
player's remaining charges (e.g. "1 / 2"), and the Reroll button disappears
once you're out. **Basic** never uses its
rerolls; **Greedy**/**Blocking** reroll whenever nothing on the board (or in
[Wildcard Roll](#wildcard-roll)'s value picker) would advance their own
strategy at all — see [Bot opponent](#bot-opponent).

### Comeback

Once the trailing player's score falls far
enough behind — the gap crosses 8% of the board's total cells (rounded up:
29/43/59 points on the 19×19/23×23/27×27 presets) — they're permanently
granted one extra [Reroll](#reroll) charge for the rest of that game. It's
its own independent charge, not an extra use of the regular Reroll budget:
it applies even if Reroll itself is off, and once granted it's never taken
away, even if that player later retakes the lead. A "Comeback! Player N gets +1 reroll"
notice marks the moment the charge is granted, and the Reroll button
appears if it wasn't already available.

## Bot opponent

Pick the opponent on the Mode Select screen: **Local 2P** for local
pass-and-play, or **Vs Bot** (Greedy is preselected) with one of the three difficulties below to play solo — the
bot rolls, places a legal piece (or continues past a forced skip), and ends
its turn on its own, with a short pause between actions. The bot always plays
Player 2 (you are Player 1), and your input is ignored while it takes its turn.

The three difficulties:
- **Basic** — picks uniformly at random among its legal placements.
- **Greedy** — prefers a placement that captures a [Prize](#prize) or
  [Steal](#steal) cell (Steal weighted double, since capturing it swings the
  score gap both ways at once), and avoids a [Pitfall](#pitfall) cell when a
  Pitfall-free placement is available; with none of those on the board, or
  when no candidate reaches one, it falls back to denying cells in your
  frontier, same as Blocking.
- **Blocking** — prefers a placement that covers cells in *your* frontier,
  denying you those spots, weighted extra heavily when one of those cells is
  a Steal cell you could otherwise have captured; falls back to a random
  pick among equally denying (or non-denying) candidates.

Greedy and Blocking also play [Wildcard Roll](#wildcard-roll) and
[Reroll](#reroll) with the same underlying strategy: on a wildcard roll they
pick whichever value scores best on their own metric (a reachable
Prize/Steal/Pitfall for Greedy, a deniable frontier cell for Blocking); if
every value ties at zero, Blocking picks randomly among them, while Greedy
instead prefers whichever value gives the larger piece. With Reroll on,
Blocking spends a charge to discard a roll that wouldn't deny you anything
right now. Greedy does the same, but only when it can't do better than a
score of zero right now — with Prize, Steal, and Pitfall all off (or none of
them reachable at all), no roll could ever score anyway, so Greedy accepts
whatever it gets instead of burning charges for nothing. Basic stays fully
random for both and never rerolls.

## Series mode

Instead of a single game, you can play a 3-round or 5-round series against
the same opponent: board size, skip limit, and mode settings (including
Prize, Walls, Obstacles, Pitfall, Steal, Wildcard Roll, Enclosure Penalty,
Reroll, and Comeback, if enabled) are locked in once for every round. Who
goes first alternates each round (Player 1 starts round 1, Player 2 starts
round 2, and so on), regardless of who won the previous round. Every
round's score (same rules as above) adds to each player's running series
total — a landslide round counts for more than a squeaker — so the whole
series is always played out, and the player with the higher cumulative
score at the end wins. Equal cumulative scores after all rounds is a
tied series. The side rail shows the running series score, each round ends on its own
result card, and the series result card lists every round's score above the
series total.

## Project structure

```
rectangles/
├── engine/               # rules engine, no UI dependency
│   ├── analysis.py       # Replay's turn analysis: where a better move existed
│   ├── board.py          # grid + placement legality
│   ├── bot.py            # picks a placement for the bot opponent (Basic/Greedy/Blocking)
│   ├── constants.py      # tunable game/UI values (board sizes, limits, presets)
│   ├── game.py           # turn state machine, scoring, game-over rules
│   ├── models.py         # Rectangle, Player, TurnRecord
│   ├── persistence.py    # save/load a game, series or tournament to a file
│   ├── series.py         # N-round match series (cumulative score, next-round setup)
│   └── tournament.py     # single-elimination bracket (participants, matches, tiebreaks)
└── server/               # FastAPI/WebSocket server for online play
    ├── app.py            # WebSocket handler, one Game per connection; serves frontend/dist
    └── schema.py         # wire message schema, state serialization
frontend/                 # React + Vite web client
└── src/
    ├── screens/          # Mode Select, Playing, Replay, and the dialogs and overlays
    ├── components/       # the board and other shared pieces
    ├── useGameSocket.ts  # the WebSocket connection and game state
    ├── usePlacementInput.ts  # mouse, touch and keyboard placement
    └── tokens.css        # colours, type and shared button styles
tests/                    # backend tests (engine/, server/); frontend tests sit beside their source
docs/GAME_SPEC.md         # the full ruleset, independent of this code
pyproject.toml            # Python dependencies and settings (managed with uv)
```

The engine also implements tournaments and save/resume (see sections 12 and 13
of the [spec](docs/GAME_SPEC.md)); the web client doesn't offer them.

The rules engine (`rectangles/engine/`) has no UI dependency, so it's fully
unit-testable headlessly — see `tests/`.
