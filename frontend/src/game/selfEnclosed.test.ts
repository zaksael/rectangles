import { expect, test } from 'vitest'
import cases from '../dev/fixtures/enclosureCases.json'
import { selfEnclosedOwners } from './selfEnclosed'

// Boards and the per-player enclosed-cell counts the engine computed for them (tests/engine/enclosure_cases.py writes the file).
// The client re-implements that flood-fill to hatch the cells, so its count must equal the engine's on every board.
type Case = (typeof cases)[number]

function hatched(board: Case) {
  const owners = new Map(board.owners.map(([r, c, p]) => [`${r},${c}`, p] as [string, number]))
  const obstacles = new Set(board.obstacles.map(([r, c]) => `${r},${c}`))
  const cells = selfEnclosedOwners(board.size, owners, obstacles, board.walls as [[number, number], [number, number]][])
  return { '1': cells.filter(([, , p]) => p === 1).length, '2': cells.filter(([, , p]) => p === 2).length }
}

test.each(cases.map((c) => [c.name, c] as const))('hatches the engine\'s enclosed cells on %s', (_name, board) => {
  expect(hatched(board)).toEqual(board.expected)
})

test('the boards include real games with enclosed cells, so the comparison is not vacuous', () => {
  const enclosed = cases.filter((c) => c.name.startsWith('a real') && c.expected['1'] + c.expected['2'] > 0)

  expect(enclosed.length).toBeGreaterThanOrEqual(4)
})
