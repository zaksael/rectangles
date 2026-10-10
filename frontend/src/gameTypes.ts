export type ErrorReason =
  | 'invalidAction'
  | 'illegalPlacement'
  | 'protocolVersionMismatch'
  | 'illegalWildcardValue'
  | 'malformedMessage'

export type TurnStateName = 'awaitingRoll' | 'choosingWildcard' | 'choosingPlacement' | 'skipped' | 'gameOver'

export type GameOverReasonName = 'boardFull' | 'skipLimit' | 'playerBlocked' | 'surrender'

export type GameAction =
  | { type: 'roll' }
  | { type: 'skip' }
  | { type: 'reroll' }
  | { type: 'surrender' }
  | { type: 'continueSeries' }
  | { type: 'chooseWildcard'; value: number }
  | { type: 'place'; topLeft: [number, number]; width: number; height: number }

export interface LegalPlacement {
  width: number
  height: number
  topLefts: [number, number][]
}

export interface PieceState {
  topLeft: [number, number]
  width: number
  height: number
  owner: number
}

interface SpecialCellRule {
  captured: number
}

export interface PlayerState {
  name: string
  board: {
    startCorner: [number, number]
    pieces: PieceState[]
    consecutiveSkips: number
  }
  score: {
    totalArea: number
    totalScore: number
    breakdown: ScoreParts
    potential: { area: number; prize: { points: number } }
  }
  houseRules: {
    reroll: { used: number; limit: number }
    comebackNudge: { granted: boolean }
    selfEnclosedPenalty: { cells: number }
    prize: SpecialCellRule
    pitfall: SpecialCellRule
    steal: SpecialCellRule
  }
}

interface SpecialCellHouseRule {
  enabled: boolean
  cells: [number, number][]
  points: number
}

// What each scoring rule adds to one player's total at a step (signed); the parts sum to that player's score.
export interface ScoreParts {
  area: number
  prize: number
  pitfall: number
  steal: number
  enclosure: number
}

export interface HistoryEntry {
  playerId: number
  roll: [number, number]
  placed: { topLeft: [number, number]; width: number; height: number } | null
  wildcardOriginalRoll: [number, number] | null
  score: { '1': number; '2': number }
  breakdown: { '1': ScoreParts; '2': ScoreParts }
}

export interface GameWireState {
  board: { size: number; skipLimit: number }
  turn: {
    currentPlayerId: number
    turnState: TurnStateName
    lastRoll: [number, number] | null
    legalPlacements: LegalPlacement[]
  }
  houseRules: {
    wildcard: {
      enabled: boolean
      originalRoll: [number, number] | null
      legalValues: number[]
      editableIndex: number | null
    }
    reroll: { enabled: boolean; canReroll: boolean }
    comebackNudge: { enabled: boolean }
    walls: { enabled: boolean; edges: [number, number][][] }
    obstacles: { enabled: boolean; cells: [number, number][] }
    prize: SpecialCellHouseRule
    pitfall: SpecialCellHouseRule
    steal: SpecialCellHouseRule
    selfEnclosedPenalty: { enabled: boolean }
  }
  players: { '1': PlayerState; '2': PlayerState }
  gameOver: {
    reason: GameOverReasonName | null
    playerId: number | null
    winner: number | null
    // One entry per move, sent only once the game is over.
    history?: HistoryEntry[] | null
  }
}

export interface SeriesWireState {
  length: number
  scores: { '1': number; '2': number }
  gamesPlayed: number
  rounds: {
    area: { '1': number; '2': number }
    prizeCaptured: { '1': number; '2': number }
    pitfallCaptured: { '1': number; '2': number }
    stealCaptured: { '1': number; '2': number }
    total: { '1': number; '2': number }
  }[]
  isComplete: boolean
  winner: number | null
}
