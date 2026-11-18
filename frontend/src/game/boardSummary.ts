import type { GameWireState } from './gameTypes'

// A wall is a straight run of cell edges, so count the runs. shortcut: two walls end to end count as one, fine until the generator can place them touching.
function wallLines(edges: GameWireState['houseRules']['walls']['edges']) {
  const lines = new Map<string, number[]>()
  for (const [[r1, c1], [r2, c2]] of edges) {
    const line = c1 === c2 ? `h${Math.max(r1, r2)}` : `v${Math.max(c1, c2)}`
    lines.set(line, [...(lines.get(line) ?? []), c1 === c2 ? c1 : r1])
  }
  let runs = 0
  for (const at of lines.values()) runs += at.sort((a, b) => a - b).filter((n, i) => i === 0 || n !== at[i - 1]! + 1).length
  return runs
}

// The board as a screen reader gets it: each player's pieces and cells, then any obstacles and walls.
export function boardSummary(game: GameWireState, cellsOf: (id: '1' | '2') => number = (id) => game.players[id].score.totalArea) {
  const count = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`
  const { obstacles, walls } = game.houseRules
  const parts = (['1', '2'] as const).map((id) => {
    const p = game.players[id]
    return `${p.name}: ${count(p.board.pieces.length, 'piece')}, ${count(cellsOf(id), 'cell')}.`
  })
  if (obstacles.enabled) parts.push(`${count(obstacles.cells.length, 'obstacle cell')}.`)
  if (walls.enabled) parts.push(`${count(wallLines(walls.edges), 'wall')}.`)
  return parts.join(' ')
}
