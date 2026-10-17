import type { GameWireState } from '../game/gameTypes'
import type { RULE_ROWS } from '../game/ruleRows'
import { enabledSpecialRules } from '../game/specialCells'

// A score-table row's label; a special-cell rule's row also carries the board's own mark and what one capture is worth.
export function RuleRowLabel({ row, game }: { row: (typeof RULE_ROWS)[number]; game: GameWireState }) {
  const special = enabledSpecialRules(game).find(({ label }) => label === row.label)
  if (!special) return row.label
  return (
    <>
      <span className={`board-cell ${special.kind} rule-mark`} aria-hidden="true" />
      {row.label} <span className="row-points">{`${special.sign}${special.points}`}</span>
    </>
  )
}
