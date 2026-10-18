export function cellKey(row: number, col: number): string {
  return `${row},${col}`
}

function wallKey(a: [number, number], b: [number, number]): string {
  return [cellKey(...a), cellKey(...b)].sort().join('|')
}

// Mirrors the engine's own self-enclosed detection: flood-fills each connected empty
// region and, if it never touches the board edge and borders exactly one player,
// marks every cell in it as enclosed by that player. The wire only sends a per-player
// count (not positions), so this is recomputed client-side from data already on hand.
export function selfEnclosedOwners(
  size: number,
  owners: Map<string, number>,
  obstacleCells: Set<string>,
  wallEdges: [number, number][][],
): [number, number, 1 | 2][] {
  const wallSet = new Set(wallEdges.map(([a, b]) => wallKey(a, b)))
  const visited = new Set<string>()
  const result: [number, number, 1 | 2][] = []

  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const startKey = cellKey(r, c)
      if (visited.has(startKey) || owners.has(startKey) || obstacleCells.has(startKey)) continue

      const region: [number, number][] = []
      const regionOwners = new Set<number>()
      let touchesEdge = false
      const queue: [number, number][] = [[r, c]]
      visited.add(startKey)

      while (queue.length) {
        const [cr, cc] = queue.shift()!
        region.push([cr, cc])
        for (const [nr, nc] of [
          [cr - 1, cc],
          [cr + 1, cc],
          [cr, cc - 1],
          [cr, cc + 1],
        ] as [number, number][]) {
          if (nr < 0 || nr >= size || nc < 0 || nc >= size) {
            touchesEdge = true
            continue
          }
          if (wallSet.has(wallKey([cr, cc], [nr, nc]))) continue
          const nKey = cellKey(nr, nc)
          const owner = owners.get(nKey)
          if (owner === undefined) {
            if (!obstacleCells.has(nKey) && !visited.has(nKey)) {
              visited.add(nKey)
              queue.push([nr, nc])
            }
          } else {
            regionOwners.add(owner)
          }
        }
      }

      if (!touchesEdge && regionOwners.size === 1) {
        const owner = [...regionOwners][0] as 1 | 2
        for (const [er, ec] of region) result.push([er, ec, owner])
      }
    }
  }
  return result
}
