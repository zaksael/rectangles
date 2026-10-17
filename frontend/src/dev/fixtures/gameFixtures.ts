import type { GameWireState, HistoryEntry, SeriesWireState } from '../../game/gameTypes'

// A history entry's potential: each player's reachable empty cells after the move (prize points left at 0).
export const reach = (one: number, two: number): HistoryEntry['potential'] => ({
  '1': { area: one, prize: { points: 0 } },
  '2': { area: two, prize: { points: 0 } },
})

// A history entry: player 1's skip with zero scores; override what a test cares about.
export const makeHistoryEntry = (overrides: Partial<HistoryEntry> = {}): HistoryEntry => {
  const zero = { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }
  return { playerId: 1, roll: [2, 2], placed: null, wildcardOriginalRoll: null, score: { '1': 0, '2': 0 }, breakdown: { '1': zero, '2': zero }, potential: reach(0, 0), ...overrides }
}

export function makeGame(overrides: Partial<GameWireState> = {}): GameWireState {
  return {
    board: { size: 3, skipLimit: 5 },
    turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [], recentTurns: [] },
    houseRules: {
      wildcard: { enabled: false, originalRoll: null, legalValues: [], editableIndex: null },
      reroll: { enabled: false, canReroll: false },
      comebackNudge: { enabled: false },
      walls: { enabled: false, edges: [] },
      obstacles: { enabled: false, cells: [] },
      prize: { enabled: false, cells: [], points: 0 },
      pitfall: { enabled: false, cells: [], points: 0 },
      steal: { enabled: false, cells: [], points: 0 },
      selfEnclosedPenalty: { enabled: false },
    },
    players: {
      '1': {
        name: 'Player 1',
        board: { startCorner: [0, 0], pieces: [], consecutiveSkips: 0 },
        score: { totalArea: 0, totalScore: 0, breakdown: { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }, potential: { area: 0, prize: { points: 0 } } },
        houseRules: {
          reroll: { used: 0, limit: 0 },
          comebackNudge: { granted: false },
          selfEnclosedPenalty: { cells: 0 },
          prize: { captured: 0 },
          pitfall: { captured: 0 },
          steal: { captured: 0 },
        },
      },
      '2': {
        name: 'Player 2',
        board: { startCorner: [2, 2], pieces: [], consecutiveSkips: 0 },
        score: { totalArea: 0, totalScore: 0, breakdown: { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }, potential: { area: 0, prize: { points: 0 } } },
        houseRules: {
          reroll: { used: 0, limit: 0 },
          comebackNudge: { granted: false },
          selfEnclosedPenalty: { cells: 0 },
          prize: { captured: 0 },
          pitfall: { captured: 0 },
          steal: { captured: 0 },
        },
      },
    },
    gameOver: { reason: null, playerId: null, winner: null, history: null },
    ...overrides,
  }
}

export function makeSeries(overrides: Partial<SeriesWireState> = {}): SeriesWireState {
  const zero = { '1': 0, '2': 0 }
  return {
    length: 3,
    scores: { ...zero },
    gamesPlayed: 1,
    rounds: [{ area: { ...zero }, prizeCaptured: { ...zero }, pitfallCaptured: { ...zero }, stealCaptured: { ...zero }, total: { ...zero } }],
    isComplete: false,
    winner: null,
    ...overrides,
  }
}
