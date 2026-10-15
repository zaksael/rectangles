import { afterAll, beforeAll, expect, test } from 'vitest'
import { WebSocket as NodeWebSocket } from 'ws'
import { makeGame, makeSeries, reach } from '../dev/fixtures/gameFixtures'
import { startServer } from '../dev/testUtils/realServer'
import { shapeDiff } from '../dev/testUtils/shapeDiff'
import type { AnalysisTurn, GameAction, HistoryEntry, RecentTurn } from '../game/gameTypes'

// The real server's payloads, key for key, against typed exemplars: tsc keeps each exemplar identical to the TS wire types, so a
// renamed, dropped or added server key (or a TS type that drifted) fails here. Values are not compared, only the key structure.

let serverUrl: string
let stopServer: () => void

beforeAll(async () => {
  ;({ serverUrl, stop: stopServer } = await startServer())
}, 15_000)

afterAll(() => stopServer())

const ALL_RULES =
  'wildcardEnabled=true&rerollEnabled=true&wallsEnabled=true&obstaclesEnabled=true&prizeEnabled=true&pitfallEnabled=true&stealEnabled=true&selfEnclosedPenaltyEnabled=true&comebackNudgeEnabled=true'

// The game's own structured messages, in order, with a helper that sends one action and waits for the reply.
async function connect(query: string) {
  const socket = new NodeWebSocket(`${serverUrl}/ws?protocolVersion=1&${query}`)
  const inbox: any[] = []
  const waiting: ((message: any) => void)[] = []
  socket.on('message', (raw) => {
    const message = JSON.parse(String(raw))
    const next = waiting.shift()
    if (next) next(message)
    else inbox.push(message)
  })
  const next = () => new Promise<any>((resolve) => (inbox.length > 0 ? resolve(inbox.shift()) : waiting.push(resolve)))
  await new Promise<void>((resolve) => socket.once('open', () => resolve()))
  return {
    first: next(),
    act: async (action: GameAction | { type: string }) => {
      socket.send(JSON.stringify({ protocolVersion: 1, ...action }))
      return next()
    },
    close: () => socket.close(),
  }
}

// Plays the legal move for whatever the turn asks, until `moves` turns are on the board or the game ends.
async function play(client: Awaited<ReturnType<typeof connect>>, state: any, moves: number) {
  for (let step = 0; step < 60 && state.game.turn.turnState !== 'gameOver'; step++) {
    if (state.game.turn.recentTurns.length >= moves) break
    const { turnState, legalPlacements } = state.game.turn
    const action: GameAction =
      turnState === 'awaitingRoll'
        ? { type: 'roll' }
        : turnState === 'choosingWildcard'
          ? { type: 'chooseWildcard', value: state.game.houseRules.wildcard.legalValues[0] }
          : turnState === 'choosingPlacement'
            ? { type: 'place', topLeft: legalPlacements[0].topLefts[0], width: legalPlacements[0].width, height: legalPlacements[0].height }
            : { type: 'skip' }
    state = await client.act(action)
  }
  return state
}

const ENTRY: HistoryEntry = {
  playerId: 1,
  roll: [2, 3],
  placed: { topLeft: [0, 0], width: 2, height: 3 },
  wildcardOriginalRoll: [1, 1],
  score: { '1': 0, '2': 0 },
  breakdown: {
    '1': { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 },
    '2': { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 },
  },
  potential: reach(0, 0),
}
const { potential: _potential, ...ENTRY_FIELDS } = ENTRY
const RECENT: RecentTurn = { ...ENTRY_FIELDS, turn: 1, points: 0 }
const ANALYSIS_TURN: AnalysisTurn = { turn: 1, axis: 'prize', chosen: 0, best: 1, topLeft: [0, 0], width: 1, height: 1 }

// An exemplar state message: makeGame's keys, with entries (empty lists and nulls stop the comparison) filled in.
const stateMessage = (over = false) => ({
  protocolVersion: 1,
  type: 'state',
  game: makeGame({
    turn: { ...makeGame().turn, recentTurns: [RECENT] },
    gameOver: { reason: null, playerId: null, winner: null, history: over ? [ENTRY] : null },
  }),
  series: makeSeries(),
})

test('a mid-game state with every rule on has the keys the TS wire types describe', async () => {
  const client = await connect(`seriesLength=3&${ALL_RULES}`)
  const state = await play(client, await client.first, 3)

  expect(state.game.turn.recentTurns.length).toBeGreaterThan(0) // the moves were played, so the entries below were compared
  expect(shapeDiff(state, stateMessage())).toEqual([])
  for (const turn of state.game.turn.recentTurns) expect(shapeDiff(turn, RECENT), `recentTurns[${turn.turn}]`).toEqual([])
  client.close()
})

test('a finished game carries history entries, the series rounds and the analysis reply in the TS shape', async () => {
  const client = await connect(`seriesLength=3&${ALL_RULES}`)
  const played = await play(client, await client.first, 4)
  const over = await client.act({ type: 'surrender' })

  expect(over.game.gameOver.history.length).toBeGreaterThan(0)
  expect(shapeDiff(over, stateMessage(true))).toEqual([])
  for (const entry of over.game.gameOver.history) expect(shapeDiff(entry, ENTRY), `history[${entry.playerId}]`).toEqual([])
  expect(over.series.rounds.length).toBeGreaterThan(0)
  expect(played.game.gameOver.history).toBeNull()

  const analysis = await client.act({ type: 'requestAnalysis' })
  expect(shapeDiff(analysis, { protocolVersion: 1, type: 'analysis', turns: [ANALYSIS_TURN] })).toEqual([])
  client.close()
}, 20_000)

test('an error reply has the keys the TS error handling reads', async () => {
  const client = await connect(ALL_RULES)
  await client.first
  const error = await client.act({ type: 'skip' }) // nothing to skip before a roll

  expect(shapeDiff(error, { protocolVersion: 1, type: 'error', reason: 'invalidAction', message: 'text' })).toEqual([])
  expect(error.reason).toBe('invalidAction')
  client.close()
})
