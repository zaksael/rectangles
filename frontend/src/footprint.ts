import type { GameWireState } from './gameTypes'
import { ownersByCell } from './placementReason'
import { specialCellKinds } from './specialCells'

const cells = (n: number, what = '') => `${n} ${what}${what ? ' ' : ''}cell${n === 1 ? '' : 's'}`

// What a w x h piece at topLeft would sit on, for a screen reader: empty cells, each side's cells, obstacles and special cells.
export function describeFootprint(game: GameWireState, playerId: 1 | 2, [row, col]: [number, number], [width, height]: [number, number]): string {
  const owners = ownersByCell(game)
  const obstacles = new Set(game.houseRules.obstacles.enabled ? game.houseRules.obstacles.cells.map(([r, c]) => `${r},${c}`) : [])
  const specials = specialCellKinds(game)

  const counts = { empty: 0, own: 0, opponent: 0, obstacle: 0, prize: 0, pitfall: 0, steal: 0 }
  for (let r = row; r < row + height; r++) {
    for (let c = col; c < col + width; c++) {
      const key = `${r},${c}`
      const owner = owners.get(key)
      if (owner === playerId) counts.own++
      else if (owner !== undefined) counts.opponent++
      else if (obstacles.has(key)) counts.obstacle++
      else counts[specials.get(key) ?? 'empty']++
    }
  }

  if (counts.empty === width * height) return cells(counts.empty, 'empty')
  const opponent = game.players[playerId === 1 ? '2' : '1'].name
  const parts = [
    counts.empty && cells(counts.empty, 'empty'),
    counts.own && `${counts.own} of your cells`,
    counts.opponent && `${counts.opponent} of ${opponent}’s cells`,
    counts.obstacle && cells(counts.obstacle, 'obstacle'),
    counts.prize && cells(counts.prize, 'prize'),
    counts.pitfall && cells(counts.pitfall, 'pitfall'),
    counts.steal && cells(counts.steal, 'steal'),
  ].filter(Boolean)
  return `${cells(width * height)}: ${parts.join(', ')}`
}
