import { expect, test } from 'vitest'
import { describeFootprint } from './footprint'
import { makeGame } from '../fixtures/gameFixtures'
import type { GameWireState } from './gameTypes'

function game(setup: (g: GameWireState) => void = () => {}): GameWireState {
  const g = makeGame({ board: { size: 6, skipLimit: 5 } })
  setup(g)
  return g
}
const piece = (owner: number, topLeft: [number, number], width: number, height: number) => ({ owner, topLeft, width, height })

test('an empty footprint counts its cells, singular for one', () => {
  expect(describeFootprint(game(), 1, [0, 0], [2, 3])).toBe('6 empty cells')
  expect(describeFootprint(game(), 1, [0, 0], [1, 1])).toBe('1 empty cell')
})

test('own and opponent cells are named, the opponent by name', () => {
  const g = game((g) => {
    g.players['1'].board.pieces = [piece(1, [0, 0], 1, 1)]
    g.players['2'].board.pieces = [piece(2, [0, 1], 2, 1)]
  })
  expect(describeFootprint(g, 1, [0, 0], [3, 1])).toBe('3 cells: 1 of your cells, 2 of Player 2’s cells')
})

test('obstacles and special cells are counted apart from empty cells', () => {
  const g = game((g) => {
    g.houseRules.obstacles = { enabled: true, cells: [[0, 0]] }
    g.houseRules.prize = { enabled: true, cells: [[0, 1]], points: 10 }
    g.houseRules.pitfall = { enabled: true, cells: [[0, 2]], points: 10 }
  })
  expect(describeFootprint(g, 1, [0, 0], [4, 1])).toBe('4 cells: 1 empty cell, 1 obstacle cell, 1 prize cell, 1 pitfall cell')
})

test('a special cell already covered by a piece is not counted as special', () => {
  const g = game((g) => {
    g.players['2'].board.pieces = [piece(2, [0, 1], 1, 1)]
    g.houseRules.prize = { enabled: true, cells: [[0, 1]], points: 10 }
  })
  expect(describeFootprint(g, 1, [0, 0], [2, 1])).toBe('2 cells: 1 empty cell, 1 of Player 2’s cells')
})

test('a special cell of a rule that is off is just an empty cell', () => {
  const g = game((g) => {
    g.houseRules.steal = { enabled: false, cells: [[0, 0]], points: 10 }
  })
  expect(describeFootprint(g, 1, [0, 0], [1, 1])).toBe('1 empty cell')
})
