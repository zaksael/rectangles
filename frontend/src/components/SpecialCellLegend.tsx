import type { GameWireState } from '../gameTypes'
import { enabledSpecialRules } from '../specialCells'

// One line under the board naming each special-cell rule that is on; the mark is drawn by the board's own rules.
export function SpecialCellLegend({ game }: { game: GameWireState }) {
  const rules = enabledSpecialRules(game)
  if (rules.length === 0) return null
  return (
    <ul className="playing-legend" aria-label="Special cells">
      {rules.map(({ kind, label, sign, points }) => (
        <li key={kind} className="playing-legend-item">
          <span className={`board-cell ${kind} playing-legend-mark`} aria-hidden="true" />
          {`${label} ${sign}${points}`}
        </li>
      ))}
    </ul>
  )
}
