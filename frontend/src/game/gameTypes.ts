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
  | { type: 'requestAnalysis' }
  | { type: 'chooseWildcard'; value: number }
  | { type: 'place'; topLeft: [number, number]; width: number; height: number }

export type AnalysisAxis = 'prize' | 'pitfall' | 'steal' | 'denial' | 'enclosure'

// One flagged move: another legal placement would have ranked higher. chosen/best are cells denied for 'denial', points otherwise.
export interface AnalysisTurn {
  turn: number
  axis: AnalysisAxis
  chosen: number
  best: number
  topLeft: [number, number]
  width: number
  height: number
}

// The replay's turn analysis; a game with nothing flagged is 'ready' with no turns. Absent (null) until asked for.
export type Analysis = { status: 'loading' } | { status: 'ready'; turns: AnalysisTurn[] } | { status: 'unavailable' }

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
    potential: Potential
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

export interface Potential {
  area: number
  prize: { points: number }
}

export interface HistoryEntry {
  playerId: number
  roll: [number, number]
  placed: { topLeft: [number, number]; width: number; height: number } | null
  wildcardOriginalRoll: [number, number] | null
  score: { '1': number; '2': number }
  breakdown: { '1': ScoreParts; '2': ScoreParts }
  potential: { '1': Potential; '2': Potential }
}

// A recent turn on every state message: a history entry plus its move number and the mover's own score change.
export interface RecentTurn extends Omit<HistoryEntry, 'potential'> { // recentTurns never carry potential
  turn: number
  points: number
}

export interface GameWireState {
  board: { size: number; skipLimit: number }
  turn: {
    currentPlayerId: number
    turnState: TurnStateName
    lastRoll: [number, number] | null
    legalPlacements: LegalPlacement[]
    // The last six turns, oldest first.
    recentTurns?: RecentTurn[]
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
