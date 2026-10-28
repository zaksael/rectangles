# WebSocket protocol

How a client talks to the server: connect parameters, the messages each side sends, and the errors. The ruleset itself is in [GAME_SPEC.md](GAME_SPEC.md); the exact shape of the `game` object is the `GameWireState` type in [`frontend/src/game/gameTypes.ts`](../frontend/src/game/gameTypes.ts).

## Connect

`GET /ws?<parameters>`, upgraded to a WebSocket. One connection is one game; closing it ends the game.

| Parameter | Values | Default |
|---|---|---|
| `protocolVersion` | `1` (required) | — |
| `boardSize` | `19`, `23`, `27` | `19` |
| `skipLimit` | `3`, `5` | `5` |
| `seriesLength` | `3`, `5` | none (a single game) |
| `botSeats` | `2` (the bot takes Player 2) | no bot |
| `botDifficulty` | `Basic`, `Greedy`, `Blocking`; used only with `botSeats` | `Basic` |
| `prizeEnabled`, `pitfallEnabled`, `stealEnabled`, `wallsEnabled`, `obstaclesEnabled`, `selfEnclosedPenaltyEnabled`, `wildcardEnabled`, `rerollEnabled`, `comebackNudgeEnabled` | `true` or `false` | `false` |

The server answers `403` and does not upgrade when a parameter is unknown, a value is not allowed, or the page's `Origin` is a different host and port than the server's (no `Origin`, as from a script, is accepted). A single game starts with a coin flip for the first player; round 1 of a series is started by Player 1.

The server sends a ping every 20 seconds so idle connections stay open.

## Messages

Every message is one JSON text frame with `"protocolVersion": 1` and a `"type"`.

### Client to server

| `type` | Extra fields | Meaning |
|---|---|---|
| `roll` | — | roll the dice |
| `place` | `topLeft` `[row, col]`, `width`, `height` | place the rolled piece |
| `skip` | — | accept a roll with no legal placement |
| `reroll` | — | discard the roll for a fresh one |
| `chooseWildcard` | `value` (1–6) | set the editable die of a wildcard roll |
| `surrender` | — | concede the game |
| `requestAnalysis` | — | ask for the turn analysis; only after the game is over |
| `continueSeries` | — | start the next round; only after a finished round of an unfinished series |

### Server to client

| `type` | Fields | When |
|---|---|---|
| `state` | `game`, `series` (`null` outside a series) | after connect and after every accepted action |
| `analysis` | `turns` | answer to `requestAnalysis` |
| `error` | `reason`, `message` | an action was refused; the game is unchanged |

With a bot, the answer to an action is one `state` per step, in order: the human's action, then each roll, placement or skip the bot makes until it is the human's turn again. A bot that moves first sends its steps right after connect. The last `state` is the current one.

`analysis.turns` lists the turns where a better move existed: `turn` (1-based), `axis` (`prize`, `pitfall`, `steal`, `denial` or `enclosure`), `chosen` and `best` (points on that axis), and the better placement as `topLeft`, `width` and `height`.

## Errors

`error.reason` is one of:

- `malformedMessage`: not JSON, an unknown `type`, or a missing or mistyped field
- `protocolVersionMismatch`: `protocolVersion` is not `1`
- `invalidAction`: the action does not fit the moment (rolling twice, any `roll`, `place`, `skip`, `reroll` or `chooseWildcard` once the game is over, `requestAnalysis` mid-game, `continueSeries` outside a finished round)
- `illegalPlacement`: the `place` is not a legal placement
- `illegalWildcardValue`: the `chooseWildcard` value is outside 1–6
