# Rectangles

A two-player pen-and-paper dice game, implemented as a Scala rules engine and WebSocket server with a React
frontend that runs in the browser.

Two players share one grid board and grow their territory inward from
opposite corners by rolling dice and placing rectangles. Whoever covers more
area when the game ends wins.

## Index

- [Requirements](#requirements)
- [Setup](#setup)
- [Play](#play)
  - [Keyboard shortcuts](#keyboard-shortcuts)
- [Accessibility](#accessibility)
- [Development](#development)
  - [Frontend development](#frontend-development)
  - [Scala server](#scala-server)
- [Tests](#tests)
- [Rules](#rules)
- [House Rules](#house-rules)
- [Bot opponent](#bot-opponent)
- [Series mode](#series-mode)
- [Project structure](#project-structure)

## Requirements

- JDK 25 (pinned in `.sdkmanrc` and `.java-version`) and sbt 2.0.10, to build and test the server
- Node.js 22.22.2, 24.15 or 26 and newer (the even-numbered LTS lines) and npm, to build and test the frontend

## Setup

```bash
cd frontend
npm install
npm run build
cd ../server-scala
sbt server/stage
```

## Play

```bash
server-scala/target/stage/bin/rectangles-server
```

Run it from the repository root, with `JAVA_HOME` set to JDK 25. Then open `http://127.0.0.1:8765/` (set `RECTANGLES_SERVER_HOST` and
`RECTANGLES_SERVER_PORT` to change the address). The server serves the built frontend from
`frontend/dist` (relative to where it runs; `RECTANGLES_FRONTEND_DIST` changes the folder) and the
game socket at `/ws` (and `GET /health`); without a build it serves only those two.

A game lives in its browser tab: the server keeps one game per connection, with no accounts, so
reloading or closing the tab ends it (the browser asks before leaving a game in progress).

The game opens on Mode Select. Pick the opponent (**Local 2P** or **Vs Bot** and
its difficulty), a board size and skip limit, how many games to play (1, 3 or
5, see [Series mode](#series-mode)), and which of the nine
[house rules](#house-rules) to switch on, then **Start Game**. Your last choices
are remembered, and **Reset to Defaults** appears once any differ. Each group
of house rules has **All On** and **All Off** links to switch its three rules together.

Playing and Replay need a window at least 1320px wide; below that a "Widen the
Window" notice takes their place and the game waits where it was.

- **Roll** (`D`) to get a piece for your turn.
- Every cell where your rolled piece could legally go is highlighted; hover
  the board (or tap, then tap again to place) to preview the exact placement,
  centered on the pointer, and click to place the piece.
- Rotate the piece with the **Rotate** button or `R`.
- A roll with no legal placement waits for you to press **Skip** (`S`) while you can still reroll it; with no reroll to use, the game skips it for you after a moment (`S` skips at once).
- A [Wildcard Roll](#house-rules) turn shows a row of value buttons (greyed
  out for any value without a legal placement) to choose the editable die's
  value before placement continues.
- With [Reroll](#house-rules) on and a charge left, **Reroll** (`E`) discards the
  current roll for a fresh one, including alongside a forced skip.
- The side rail shows both scores with a row for each scoring rule that is
  on (the Prize, Pitfall and Steal rows show the cell's mark and what a capture
  is worth), each player's skip streak, and the latest moves.
- **Menu** (`M`) shows the match settings and has **Resume** and
  **Surrender**; surrender always asks for confirmation first, and your
  opponent wins regardless of the area tally.
- When the game ends, a summary shows the winner (or tie), final scores, the
  score breakdown and the reason the game ended. **View Board** (`V`) looks at
  the final board with a slim result bar, **Replay** (`R`) steps through the
  game, and **New Game** (`N`) returns to Mode Select. During a series the
  button reads **Next Round** until the series itself is decided, then **Series
  Result**.
- **Replay** the finished game turn by turn: step with First/Prev/Next/Last,
  seeing each turn's roll, placement and
  each player's score breakdown at that point (the Prize, Pitfall and Steal
  rows carry the cell's mark and what a capture is worth), plus a score-history chart
  across the whole game (click or arrow along it to jump to a turn). For the
  turn just taken, a flag appears if the best other legal option that roll
  would have scored higher than what was actually played, showing the actual
  score against the best one (e.g. "Scored 4 this turn; the best move
  scored 14 (Prize)") — or, when the difference is purely strategic
  denial rather than real points, the cells denied instead (e.g. "Denied 1
  cell this turn; the best move denied 5"). Toggle **Show Better Option** to
  outline the better placement on the board, tagged *Better move*. **Play** advances automatically
  at the Slow/Normal/Fast pace you pick; it stops at the last step, and any
  manual navigation pauses it. **Back** returns to the summary.

### Keyboard shortcuts

| Screen | Key | Action |
|---|---|---|
| Playing | `D` | Roll |
| Playing | `R` | Rotate the piece |
| Playing | `S` | Skip a roll with no legal placement |
| Playing | `E` | Reroll |
| Playing | `M` | Menu |
| Playing, board focused | Arrows | Move the piece |
| Playing, board focused | `N` / `Shift+N` | Jump to the next / previous legal spot |
| Playing, board focused | `Enter` or `Space` | Place the piece |
| Game over | `V` | View Board |
| Game over | `R` | Replay |
| Game over | `N` | New Game, or Next Round / Series Result in a series |
| Replay | Arrows, `Home`, `End` | Step: previous, next, first, last |
| Replay | `Space` | Play or pause |
| Replay | `Esc` | Back to the summary |
| Replay, chart focused | Arrows, `Home`, `End`, `Enter` | Move along the chart, jump to a turn |

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

Run the server in one terminal (the staged launcher, or `sbt server/run` in `server-scala/`) and
`npm run dev` in `frontend/` in another. The Vite dev server forwards `/ws` to
the server on port 8765; open the printed `localhost` URL to play. The server
accepts a WebSocket only from a page served from its own host and port, which
the Vite proxy preserves.

### Scala server

`server-scala/` holds the engine and the server. It is an sbt build with two subprojects, `core`
(rules, no server dependency) and `server` (HTTP and WebSocket).

- JDK 25 (pinned in `.sdkmanrc` and `.java-version`), sbt 2.0.10 (`server-scala/project/build.properties`) and Scala 3.9.0.
- Homebrew's `sbt` wrapper defaults `JAVA_HOME` to its own newest JDK, so export `JAVA_HOME` for JDK 25 first (`export JAVA_HOME=$(/usr/libexec/java_home -v 25)`).
- Run it from `server-scala/` with `sbt server/run`, or `sbt "~server/reStart"` to restart on every source change. It serves `GET /health` (answers `ok`), the game socket at `/ws` and the built frontend, on `127.0.0.1:8765`; `RECTANGLES_SERVER_HOST` and `RECTANGLES_SERVER_PORT` change the address and `RECTANGLES_FRONTEND_DIST` the frontend folder (from `server-scala/` it must be `../frontend/dist`; the startup log names the folder it serves, or warns that it is missing). It logs plain text to stdout; `LOGGING4S_CONSOLE_FORMAT=json` switches to JSON lines. sbt's background server keeps the environment of the call that started it, so run `sbt shutdown` before restarting with a new value.
- `server-scala/server/src/test/resources/golden/` holds recorded wire sessions (the messages sent and received, and the random draws behind them) that `GoldenReplaySpec` replays through a real session. They were recorded from the original Python implementation, which is kept at the `python-reference` tag, and stay as regression fixtures; nothing rewrites them yet.
- `frontend/src/dev/fixtures/enclosureCases.json` holds boards with their enclosed-cell counts: `EnclosureCasesSpec` checks the engine against them and the frontend's flood fill is checked against the same file. Rewrite it after changing the enclosure rule with `sbt "server/Test/runMain dev.zaksael.rectangles.server.generateEnclosureCases"` from `server-scala/`.
- `sbt server/stage` builds a launcher at `server-scala/target/stage/bin/rectangles-server`. The frontend integration tests start it by default; set `RECTANGLES_SERVER_CMD` to a command (split on whitespace, run from the repo root) to run them against another server that speaks [the protocol](docs/PROTOCOL.md), for example `RECTANGLES_SERVER_CMD=server-scala/target/stage/bin/rectangles-server npm test` from `frontend/`.
- `docker build -t rectangles-server .` builds the image: node builds `frontend/`, sbt stages the server, and a JRE 25 stage runs it as a non-root user on port 8765, with a healthcheck on `/health`. The container listens on all interfaces and logs JSON lines; `docker run -p 8765:8765 rectangles-server` then serves the game at `http://127.0.0.1:8765/`.
- Check the style from `server-scala/` with `sbt "scalafmtCheckAll; scalafixAll --check"` (format with `sbt scalafmtAll`, fix with `sbt scalafixAll`); the compiler runs with warnings fatal, and `var`, `null` and `throw` are compile errors.
- Run the tests from `server-scala/` with `sbt testFull`. Plain `sbt test` caches its result, so a re-run with no changes prints no summary.
- `sbt -batch` already goes through sbt 2's built-in thin client: a warm run takes about half a second, a cold start about 35 seconds. There is no separate `sbtn` to install.

## Tests

```bash
cd server-scala
sbt testFull                   # backend: engine and server
cd ../frontend
npm test                       # frontend (Vitest); needs `sbt server/stage` first
npm run coverage               # the same suite with a coverage report
npm run lint
```

On every push and pull request, GitHub Actions (`.github/workflows/ci.yml`) runs three jobs: the frontend lint, Vitest suite and production build; the Scala format and lint checks, tests and `sbt server/stage`, followed by the two frontend integration tests against the staged launcher; and the Docker build, followed by starting the container, waiting for it to report healthy, loading the page and connecting to the game socket.

## Rules

For a precise, implementation-agnostic reference covering every rule and
optional mode in full detail, see [docs/GAME_SPEC.md](docs/GAME_SPEC.md).

- The board is a shared grid (size configurable before each match). Player 1
  grows inward from the **top-left** corner; Player 2 grows inward from the
  **bottom-right** corner.
- Players alternate turns; in a single game a coin flip picks who goes first (a series
  alternates, starting with Player 1). On your turn, roll two
  six-sided dice — the two numbers become the width and height of a rectangle
  (rotatable, so a 2-and-5 roll can be placed as 2×5 or 5×2).
- Your first piece must be anchored exactly at your own starting corner.
  Every piece after that must be placed edge-adjacent to a piece you already
  own — touching only your opponent's territory doesn't count.
- If a roll can't legally be placed anywhere (in either orientation), your
  turn is skipped.
- Rolling doubles (both dice show the same number) triggers a
  [Wildcard Roll](#house-rules), if that optional mode is on.
- The game ends when any of the following happens:
  - neither player has any legal placement left anywhere on the board,
  - one player becomes completely boxed in by the opponent's territory (no
    empty cell touches their own anymore) even if empty cells remain
    elsewhere on the board, or
  - one player is skipped several turns in a row (configurable before each
    match, 5 by default), or
  - one player surrenders, in which case the other player wins outright
    regardless of area covered so far.
- Otherwise, the higher score wins (area, plus or minus the points from any
  [special cells](#house-rules)); equal scores are a tie.

## House Rules

Nine optional modes, toggled independently on the Mode Select screen before a
match begins. All nine start switched on the first time; after that your last
choice is kept. Special cells are seeded in mirrored pairs through the board's centre, kept clear of
both starting corners and of each other, so neither player starts closer to one than the other. For
the full wording of every rule see [docs/GAME_SPEC.md](docs/GAME_SPEC.md).

| Rule | What it does | On the board |
|---|---|---|
| **Prize** | Four cells (two mirrored pairs). Covering one captures it for +10 points on top of your area; one piece can capture several. | A plus mark that disappears once covered; a ring around what your last placement captured. |
| **Walls** | Several wall lines (mirrored pairs, horizontal or vertical) between cells, so no area is lost. A piece can't cross a wall, and a piece on one side doesn't touch territory on the other: build around the ends. | Thick lines between cells. |
| **Obstacles** | Four cells (two mirrored pairs) that no piece can ever cover. | A solid dark square. |
| **Pitfall** | Four cells (two mirrored pairs). Covering one docks you 10 points; scores aren't floored at 0, so a player can go negative. | A bar mark that disappears once covered; its own Pitfall row in the score table. |
| **Steal** | Two cells (one mirrored pair). Covering one is zero-sum: you gain 10 and your opponent loses 10, a 20-point swing. Scores can go negative. | A plus-over-minus mark that disappears once covered; the Steal row shows each player's net swing. |
| **Wildcard Roll** | Every double becomes a wildcard roll: one of the two numbers (picked at random) is yours to change to any value 1–6, the other stays fixed. If no value could fit, the pick is skipped and the turn resolves to a skip. | A row of value buttons, greyed out for values without a legal placement. |
| **Enclosure Penalty** | Each empty cell fully surrounded by your own territory docks you 1 point, recomputed after every move. Filling the hole drops the penalty. A gap bordered by both players, by neither, or touching the board's edge is never penalized. | Enclosed cells hatched in your colour; the Enclosure row in the score table. |
| **Reroll** | Two rerolls per player per game (not per series round) to discard both dice and roll again, while placing, while picking a wildcard value, or when a roll would skip your turn. | The Rerolls row shows what's left (also with Reroll off and Comeback on, where it reads 0 / 0 until a grant), and the Reroll button disappears at zero. |
| **Comeback** | When the trailing player falls behind by 8% of the board's cells (rounded up: 29/43/59 points on 19×19/23×23/27×27), they're permanently granted one extra reroll charge for that game, even if Reroll itself is off. | A "Comeback! Player N gets +1 reroll" notice. |

## Bot opponent

Pick the opponent on the Mode Select screen: **Local 2P** for local
pass-and-play, or **Vs Bot** (Greedy is preselected) with one of the three difficulties below to play solo — the
bot rolls, places a legal piece (or continues past a forced skip), and ends
its turn on its own, with a short pause between actions. The bot always plays
Player 2 (you are Player 1), and your input is ignored while it takes its turn.
In a single game a coin flip decides who moves first, so the bot opens half the time.

The three difficulties:
- **Basic** — picks uniformly at random among its legal placements.
- **Greedy** — prefers a placement that captures a [Prize](#house-rules) or
  [Steal](#house-rules) cell (Steal weighted double, since capturing it swings the
  score gap both ways at once), and avoids a [Pitfall](#house-rules) cell when a
  Pitfall-free placement is available; with none of those on the board, or
  when no candidate reaches one, it falls back to denying cells in your
  frontier, same as Blocking.
- **Blocking** — prefers a placement that covers cells in *your* frontier,
  denying you those spots. It also grabs Prize and Steal cells and avoids
  Pitfall cells the way Greedy does, weighing them against the denial; falls
  back to a random pick among equal candidates.

Greedy and Blocking also play [Wildcard Roll](#house-rules) and
[Reroll](#house-rules) with the same underlying strategy: on a wildcard roll they
pick whichever value scores best on their own metric (a reachable
Prize/Steal/Pitfall for Greedy, a deniable frontier cell for Blocking); if
every value ties at zero, Blocking picks randomly among them, while Greedy
instead prefers whichever value gives the larger piece. With Reroll on,
they spend a charge to discard a roll that would cost them points (a forced
Pitfall), or that scores nothing while a Prize or Steal (Greedy) or a cell of
your frontier (Blocking) is still within a roll's reach; with nothing in
reach, as on the opening turns, they accept the roll and keep the charge.
Basic stays fully random for both and never rerolls.

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
server-scala/
├── core/                 # rules engine, no server dependency
│   └── src/main/scala/dev/zaksael/rectangles/
│       ├── domain/       # board, game state, players, rules and constants
│       └── rules/        # placement, turns, scoring, setup, bot, analysis, series
└── server/               # HTTP and WebSocket server
    └── src/main/scala/dev/zaksael/rectangles/server/
        ├── http/         # /health, /ws and the static frontend
        ├── protocol/     # wire messages and state serialization
        └── session/      # one game per connection, action dispatch, connect parameters
frontend/                 # React + Vite web client
└── src/
    ├── screens/          # Mode Select, Playing and Replay
    ├── dialogs/          # confirmations, settings, game-over and connection overlays
    ├── components/       # the board, score chart and other shared pieces
    ├── hooks/            # the WebSocket connection, placement input and other hooks
    ├── game/             # wire types, house rules and other logic with no React
    ├── dev/              # fixtures and test helpers, not shipped
    └── tokens.css        # colours, type and shared button styles
docs/GAME_SPEC.md         # the full ruleset, independent of this code
docs/PROTOCOL.md          # the WebSocket messages between client and server
Dockerfile                # the server and the built frontend in one image
```

Tournaments (see section 12 of the [spec](docs/GAME_SPEC.md)) aren't implemented; the web client
doesn't offer them.

The rules engine (`server-scala/core/`) has no dependency on the server, so it's fully
unit-testable headlessly — see `core/src/test/`.
