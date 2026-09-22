import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../testUtils/gameFixtures'
import { Board } from './Board'

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

test('calls onCellHover with the hovered cell', () => {
  const onCellHover = vi.fn()
  const { container } = render(<Board game={makeGame()} onCellHover={onCellHover} />)

  fireEvent.mouseEnter(container.querySelector('[data-cell="1,2"]')!)

  expect(onCellHover).toHaveBeenCalledWith([1, 2])
})

test('calls onCellClick with the clicked cell', () => {
  const onCellClick = vi.fn()
  const { container } = render(<Board game={makeGame()} onCellClick={onCellClick} />)

  fireEvent.click(container.querySelector('[data-cell="2,0"]')!)

  expect(onCellClick).toHaveBeenCalledWith([2, 0])
})

test('renders a preview box at previewTopLeft sized to previewDims', () => {
  const { container } = render(<Board game={makeGame()} previewTopLeft={[1, 0]} previewDims={[2, 1]} />)

  const preview = container.querySelector('.preview')
  expect(preview).toHaveStyle({ left: '0px', top: '44px', width: '88px', height: '44px' })
})

test('renders no preview box when previewTopLeft is not given', () => {
  const { container } = render(<Board game={makeGame()} />)

  expect(container.querySelector('.preview')).not.toBeInTheDocument()
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
