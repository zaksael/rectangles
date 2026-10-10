import type { GameWireState } from './gameTypes'
import { formatSigned } from './screens/GameOverOverlay'

// One score-table row per scoring rule, in order; a row shows only while its rule is on (Replay and Playing share them).
export const RULE_ROWS = [
  { label: 'Prize', part: 'prize', on: (g: GameWireState) => g.houseRules.prize.enabled },
  { label: 'Pitfall', part: 'pitfall', on: (g: GameWireState) => g.houseRules.pitfall.enabled },
  { label: 'Steal', part: 'steal', on: (g: GameWireState) => g.houseRules.steal.enabled },
  { label: 'Enclosure', part: 'enclosure', on: (g: GameWireState) => g.houseRules.selfEnclosedPenalty.enabled },
] as const

export const signed = (n: number) => (n > 0 ? `+${n}` : formatSigned(n))
