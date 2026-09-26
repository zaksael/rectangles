import type { GameWireState } from './gameTypes'

// Lowercase: each is appended after the status line's em dash. The idle hint (no spot hovered yet)
// reuses the two rule reasons, so the same rule reads the same whether or not a spot is hovered.
export const START_CORNER_RULE = 'your first piece must cover your starting corner'
export const ADJACENCY_RULE = 'must share an edge with your territory'

// Why a candidate piece isn't placeable, by the legality rules in order (overlap, then the rest), or
// null when none of them explains it. Only used to explain an illegal hover; the server stays the judge.
export function placementReason(
  game: GameWireState,
  playerId: 1 | 2,
  [row, col]: [number, number],
  [width, height]: [number, number],
): string | null {
  const owners = new Map<string, number>()
  for (const id of ['1', '2'] as const) {
    for (const p of game.players[id].board.pieces) {
      for (let r = p.topLeft[0]; r < p.topLeft[0] + p.height; r++) {
        for (let c = p.topLeft[1]; c < p.topLeft[1] + p.width; c++) owners.set(`${r},${c}`, p.owner)
      }
    }
  }

  for (let r = row; r < row + height; r++) {
    for (let c = col; c < col + width; c++) {
      const owner = owners.get(`${r},${c}`)
      if (owner === playerId) return 'overlaps your territory'
      if (owner !== undefined) return `overlaps ${game.players[String(owner) as '1' | '2'].name}’s territory`
    }
  }

  const covers = ([r, c]: [number, number]) => r >= row && r < row + height && c >= col && c < col + width
  const { obstacles, walls } = game.houseRules
  if (obstacles.enabled && obstacles.cells.some(covers)) return 'covers an obstacle'
  if (walls.enabled && walls.edges.some(([a, b]) => covers(a) && covers(b))) return 'crosses a wall'

  const own = game.players[String(playerId) as '1' | '2'].board
  if (own.pieces.length === 0) {
    const [sr, sc] = own.startCorner
    const atCorner = (sr === row || sr === row + height - 1) && (sc === col || sc === col + width - 1)
    return atCorner ? null : START_CORNER_RULE
  }

  // A shared edge counts only if no wall sits between the two cells.
  const wallKeys = new Set(walls.enabled ? walls.edges.flatMap(([a, b]) => [`${a}|${b}`, `${b}|${a}`]) : [])
  for (let r = row; r < row + height; r++) {
    for (let c = col; c < col + width; c++) {
      for (const n of [[r - 1, c], [r + 1, c], [r, c - 1], [r, c + 1]] as [number, number][]) {
        if (owners.get(`${n[0]},${n[1]}`) === playerId && !wallKeys.has(`${[r, c]}|${n}`)) return null
      }
    }
  }
  return ADJACENCY_RULE
}
