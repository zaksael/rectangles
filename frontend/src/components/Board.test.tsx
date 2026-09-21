import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import type { GameWireState } from '../gameTypes'
import { Board } from './Board'

function makeGame(overrides: Partial<GameWireState> = {}): GameWireState {
  return {
    board: { size: 3, skipLimit: 5 },
    turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] },
    houseRules: {
      wildcard: { enabled: false, originalRoll: null, legalValues: [], editableIndex: null },
      reroll: { enabled: false, canReroll: false },
      comebackNudge: { enabled: false },
      walls: { enabled: false, edges: [] },
      obstacles: { enabled: false, cells: [] },
      prize: { enabled: false, cells: [], points: 0 },
      pitfall: { enabled: false, cells: [], points: 0 },
      steal: { enabled: false, cells: [], points: 0 },
      selfEnclosedPenalty: { enabled: false },
    },
    players: {
      '1': {
        name: 'Player 1',
        board: { startCorner: [0, 0], pieces: [], consecutiveSkips: 0 },
        score: { totalArea: 0, totalScore: 0, potential: { area: 0, prize: { points: 0 } } },
        houseRules: {
          reroll: { used: 0, limit: 0 },
          comebackNudge: { granted: false },
          selfEnclosedPenalty: { cells: 0 },
          prize: { captured: 0 },
          pitfall: { captured: 0 },
          steal: { captured: 0 },
        },
      },
      '2': {
        name: 'Player 2',
        board: { startCorner: [2, 2], pieces: [], consecutiveSkips: 0 },
        score: { totalArea: 0, totalScore: 0, potential: { area: 0, prize: { points: 0 } } },
        houseRules: {
          reroll: { used: 0, limit: 0 },
          comebackNudge: { granted: false },
          selfEnclosedPenalty: { cells: 0 },
          prize: { captured: 0 },
          pitfall: { captured: 0 },
          steal: { captured: 0 },
        },
      },
    },
    gameOver: { reason: null, playerId: null, winner: null },
    ...overrides,
  }
}

test('renders one cell per board square', () => {
  const { container } = render(<Board game={makeGame()} />)
  expect(container.querySelectorAll('.board-cell')).toHaveLength(9)
})

test('exposes the grid as an accessible role with a size label', () => {
  render(<Board game={makeGame()} />)
  expect(screen.getByRole('grid', { name: '3×3 board' })).toBeInTheDocument()
})

test('marks a cell covered by a player 1 piece with p1-fill', () => {
  const game = makeGame()
  game.players['1'].board.pieces = [{ topLeft: [0, 0], width: 2, height: 1, owner: 1 }]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('[data-cell="0,0"]')).toHaveClass('p1-fill')
  expect(container.querySelector('[data-cell="0,1"]')).toHaveClass('p1-fill')
  expect(container.querySelector('[data-cell="0,2"]')).not.toHaveClass('p1-fill')
})

test('marks a cell covered by a player 2 piece with p2-fill', () => {
  const game = makeGame()
  game.players['2'].board.pieces = [{ topLeft: [2, 2], width: 1, height: 1, owner: 2 }]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('[data-cell="2,2"]')).toHaveClass('p2-fill')
})

test('marks an obstacle cell only when the obstacles house rule is enabled', () => {
  const game = makeGame()
  game.houseRules.obstacles = { enabled: true, cells: [[1, 1]] }

  const { container } = render(<Board game={game} />)
  expect(container.querySelector('[data-cell="1,1"]')).toHaveClass('obstacle')

  game.houseRules.obstacles.enabled = false
  const { container: containerDisabled } = render(<Board game={game} />)
  expect(containerDisabled.querySelector('[data-cell="1,1"]')).not.toHaveClass('obstacle')
})

test.each(['prize', 'pitfall', 'steal'] as const)('marks a %s cell when that house rule is enabled', (kind) => {
  const game = makeGame()
  game.houseRules[kind] = { enabled: true, cells: [[0, 1]], points: 5 }

  const { container } = render(<Board game={game} />)
  expect(container.querySelector('[data-cell="0,1"]')).toHaveClass(kind)
})

test('renders one wall element per edge when the walls house rule is enabled', () => {
  const game = makeGame()
  game.houseRules.walls = {
    enabled: true,
    edges: [
      [
        [0, 1],
        [0, 2],
      ],
    ],
  }

  const { container } = render(<Board game={game} />)
  expect(container.querySelectorAll('.wall')).toHaveLength(1)
})

test('renders no walls when the walls house rule is disabled, even with edge data present', () => {
  const game = makeGame()
  game.houseRules.walls = {
    enabled: false,
    edges: [
      [
        [0, 1],
        [0, 2],
      ],
    ],
  }

  const { container } = render(<Board game={game} />)
  expect(container.querySelectorAll('.wall')).toHaveLength(0)
})

test('renders one outline per piece across both players', () => {
  const game = makeGame()
  game.players['1'].board.pieces = [{ topLeft: [0, 0], width: 2, height: 1, owner: 1 }]
  game.players['2'].board.pieces = [
    { topLeft: [2, 2], width: 1, height: 1, owner: 2 },
    { topLeft: [1, 2], width: 1, height: 1, owner: 2 },
  ]

  const { container } = render(<Board game={game} />)
  expect(container.querySelectorAll('.piece-outline')).toHaveLength(3)
})
