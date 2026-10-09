import type { GameWireState, HistoryEntry } from '../gameTypes'
import type { GameState } from '../useGameSocket'
import { makeGame, makeSeries } from './gameFixtures'

// One realistic 10x10 mid-game position shared by every fixture; only the turn state differs.
function midGame(): GameWireState {
  const base = makeGame()
  const player = (id: '1' | '2', corner: [number, number], pieces: GameWireState['players']['1']['board']['pieces'], area: number) => ({
    ...base.players[id],
    board: { startCorner: corner, pieces, consecutiveSkips: 0 },
    score: { totalArea: area, totalScore: area, potential: { area: 20, prize: { points: 0 } } },
    houseRules: { ...base.players[id].houseRules, reroll: { used: 0, limit: 2 } },
  })
  return makeGame({
    board: { size: 10, skipLimit: 5 },
    houseRules: {
      ...base.houseRules,
      reroll: { enabled: true, canReroll: false },
      comebackNudge: { enabled: true },
      obstacles: { enabled: true, cells: [[4, 4]] },
      prize: { enabled: true, cells: [[4, 5]], points: 5 },
      pitfall: { enabled: true, cells: [[6, 3]], points: 3 },
      steal: { enabled: true, cells: [[2, 7]], points: 4 },
    },
    players: {
      '1': player('1', [0, 0], [
        { topLeft: [0, 0], width: 4, height: 3, owner: 1 },
        { topLeft: [3, 0], width: 2, height: 3, owner: 1 },
      ], 18),
      '2': player('2', [9, 9], [
        { topLeft: [8, 6], width: 4, height: 2, owner: 2 },
        { topLeft: [5, 8], width: 2, height: 3, owner: 2 },
      ], 14),
    },
  })
}

// The mid-game position's four pieces in play order, then a skip; a real game can't be driven to a given step in a browser.
const move = (playerId: number, topLeft: [number, number], width: number, height: number, score: [number, number]): HistoryEntry => ({
  playerId,
  roll: [width, height],
  placed: { topLeft, width, height },
  wildcardOriginalRoll: null,
  score: { '1': score[0], '2': score[1] },
})
const HISTORY: HistoryEntry[] = [
  move(1, [0, 0], 4, 3, [12, 0]),
  move(2, [8, 6], 4, 2, [12, 8]),
  move(1, [3, 0], 2, 3, [18, 8]),
  move(2, [5, 8], 2, 3, [18, 14]),
  { playerId: 1, roll: [6, 6], placed: null, wildcardOriginalRoll: null, score: { '1': 18, '2': 14 } },
]

function gameOver(): GameWireState {
  const game = midGame()
  return {
    ...game,
    turn: { ...game.turn, turnState: 'gameOver' },
    gameOver: { reason: 'boardFull', playerId: null, winner: 1, history: HISTORY },
  }
}

const round = (a: number, b: number) => ({
  area: { '1': a, '2': b },
  prizeCaptured: { '1': 0, '2': 0 },
  pitfallCaptured: { '1': 0, '2': 0 },
  stealCaptured: { '1': 0, '2': 0 },
  total: { '1': a, '2': b },
})

const BUILDERS: Record<string, () => GameState> = {
  wildcard: () => {
    const game = midGame()
    return {
      game: {
        ...game,
        turn: { ...game.turn, turnState: 'choosingWildcard', lastRoll: [3, 4] },
        houseRules: {
          ...game.houseRules,
          wildcard: { enabled: true, originalRoll: [3, 4], legalValues: [2, 3, 4, 5], editableIndex: 0 },
        },
      },
      series: null,
    }
  },
  placing: () => {
    const game = midGame()
    return {
      game: {
        ...game,
        turn: { ...game.turn, turnState: 'choosingPlacement', lastRoll: [2, 2], legalPlacements: [{ width: 2, height: 2, topLefts: [[0, 4], [4, 5]] }] },
      },
      series: null,
    }
  },
  deadroll: () => {
    const game = midGame()
    return { game: { ...game, turn: { ...game.turn, turnState: 'skipped', lastRoll: [6, 6] } }, series: null }
  },
  gameover: () => ({ game: gameOver(), series: null }),
  series: () => ({
    game: gameOver(),
    series: makeSeries({ scores: { '1': 18, '2': 14 }, gamesPlayed: 1, rounds: [round(18, 14)] }),
  }),
  seriesplay: () => ({
    game: midGame(),
    series: makeSeries({ scores: { '1': 18, '2': 14 }, gamesPlayed: 1, rounds: [round(18, 14)] }),
  }),
  'series-loserlead': () => ({
    game: gameOver(),
    series: makeSeries({ scores: { '1': 30, '2': 33 }, gamesPlayed: 2, rounds: [round(12, 19), round(18, 14)] }),
  }),
  'series-final': () => ({
    game: gameOver(),
    series: makeSeries({
      scores: { '1': 49, '2': 41 },
      gamesPlayed: 3,
      rounds: [round(18, 14), round(13, 16), round(18, 11)],
      isComplete: true,
      winner: 1,
    }),
  }),
}

export function buildFixture(name: string): GameState | null {
  return Object.hasOwn(BUILDERS, name) ? BUILDERS[name]() : null
}

export function fixtureNameFromSearch(search: string): string | null {
  const name = new URLSearchParams(search).get('fixture')
  return name && Object.hasOwn(BUILDERS, name) ? name : null
}
