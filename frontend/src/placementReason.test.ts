import { expect, test } from 'vitest'
import type { GameWireState } from './gameTypes'
import { placementReason } from './placementReason'
import { makeGame } from './testUtils/gameFixtures'

// 6x6 board; player 1 starts top-left, player 2 bottom-right (the fixture's corners are for 3x3).
function game(setup: (g: GameWireState) => void = () => {}): GameWireState {
  const g = makeGame({ board: { size: 6, skipLimit: 5 } })
  g.players['2'].board.startCorner = [5, 5]
  setup(g)
  return g
}
const piece = (owner: number, topLeft: [number, number], width: number, height: number) => ({ owner, topLeft, width, height })

test('names the opponent when the piece overlaps their territory', () => {
  const g = game((g) => {
    g.players['1'].board.pieces = [piece(1, [0, 0], 2, 2)]
    g.players['2'].board.pieces = [piece(2, [2, 2], 2, 2)]
  })

  expect(placementReason(g, 1, [2, 1], [2, 2])).toBe('Overlaps Player 2’s territory')
})

test('says your own territory when the piece overlaps it', () => {
  const g = game((g) => {
    g.players['1'].board.pieces = [piece(1, [0, 0], 2, 2)]
  })

  expect(placementReason(g, 1, [1, 1], [2, 2])).toBe('Overlaps your territory')
})

test('says when the piece covers an obstacle', () => {
  const g = game((g) => {
    g.houseRules.obstacles = { enabled: true, cells: [[1, 1]] }
  })

  expect(placementReason(g, 1, [0, 0], [2, 2])).toBe('Covers an obstacle')
})

test('ignores obstacle cells while Obstacles is off', () => {
  const g = game((g) => {
    g.houseRules.obstacles = { enabled: false, cells: [[1, 1]] }
  })

  expect(placementReason(g, 1, [0, 0], [2, 2])).toBeNull()
})

test('says when the piece crosses a wall', () => {
  const g = game((g) => {
    g.houseRules.walls = { enabled: true, edges: [[[0, 1], [0, 2]]] }
  })

  expect(placementReason(g, 1, [0, 0], [3, 1])).toBe('Crosses a wall')
})

test('a piece that sits on one side of a wall is fine', () => {
  const g = game((g) => {
    g.houseRules.walls = { enabled: true, edges: [[[0, 1], [0, 2]]] }
  })

  expect(placementReason(g, 1, [0, 0], [2, 1])).toBeNull()
})

test('the first piece must include your starting corner', () => {
  const g = game()

  expect(placementReason(g, 1, [2, 2], [2, 2])).toBe('Your first piece must cover your starting corner')
  expect(placementReason(g, 1, [0, 0], [2, 2])).toBeNull()
  expect(placementReason(g, 2, [4, 4], [2, 2])).toBeNull()
})

test('a later piece must share an edge with your own territory', () => {
  const g = game((g) => {
    g.players['1'].board.pieces = [piece(1, [0, 0], 2, 2)]
  })

  expect(placementReason(g, 1, [0, 2], [1, 2])).toBeNull()
  expect(placementReason(g, 1, [3, 3], [1, 1])).toBe('Must share an edge with your territory')
})

test('touching only a corner or only the opponent is not enough', () => {
  const g = game((g) => {
    g.players['1'].board.pieces = [piece(1, [0, 0], 2, 2)]
    g.players['2'].board.pieces = [piece(2, [4, 4], 2, 2)]
  })

  expect(placementReason(g, 1, [2, 2], [1, 1])).toBe('Must share an edge with your territory')
  expect(placementReason(g, 1, [3, 4], [1, 1])).toBe('Must share an edge with your territory')
})

test('a wall between the two cells means the edge does not count', () => {
  const g = game((g) => {
    g.players['1'].board.pieces = [piece(1, [0, 0], 2, 2)]
    g.houseRules.walls = { enabled: true, edges: [[[0, 1], [0, 2]]] }
  })

  expect(placementReason(g, 1, [0, 2], [1, 1])).toBe('Must share an edge with your territory')
})
