import type { GameWireState } from '../gameTypes'

export function makeGame(overrides: Partial<GameWireState> = {}): GameWireState {
  return {
    board: { size: 3, skipLimit: 5 },
    turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] },
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
        score: { totalArea: 0, totalScore: 0, potential: { area: 0, prize: { points: 0 } } },
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
        score: { totalArea: 0, totalScore: 0, potential: { area: 0, prize: { points: 0 } } },
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
    gameOver: { reason: null, playerId: null, winner: null },
    ...overrides,
  }
}
