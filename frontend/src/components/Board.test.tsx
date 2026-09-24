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

test('calls onCellTap with the tapped cell and pointer type', () => {
  const onCellTap = vi.fn()
  const { container } = render(<Board game={makeGame()} onCellTap={onCellTap} />)

  fireEvent.pointerUp(container.querySelector('[data-cell="2,0"]')!, { pointerType: 'touch' })

  expect(onCellTap).toHaveBeenCalledWith([2, 0], 'touch')
})

test('marks each cell in coverableCells with the coverable class', () => {
  const { container } = render(
    <Board
      game={makeGame()}
      coverableCells={[
        [0, 0],
        [1, 2],
      ]}
    />,
  )

  expect(container.querySelector('[data-cell="0,0"]')).toHaveClass('coverable')
  expect(container.querySelector('[data-cell="1,2"]')).toHaveClass('coverable')
  expect(container.querySelector('[data-cell="0,1"]')).not.toHaveClass('coverable')
})

// A grid box as the custom properties the stylesheet turns into pixels.
const box = (el: Element | null) => {
  const style = (el as HTMLElement).style
  return { r: style.getPropertyValue('--r'), c: style.getPropertyValue('--c'), w: style.getPropertyValue('--w'), h: style.getPropertyValue('--h') }
}

test('renders a preview box at previewTopLeft sized to previewDims', () => {
  const { container } = render(<Board game={makeGame()} previewTopLeft={[1, 0]} previewDims={[2, 1]} />)

  expect(box(container.querySelector('.preview'))).toEqual({ r: '1', c: '0', w: '2', h: '1' })
})

test('exposes the board size so the stylesheet can size the cells to the viewport', () => {
  const { container } = render(<Board game={makeGame({ board: { size: 19, skipLimit: 5 } })} />)

  expect((container.querySelector('.board') as HTMLElement).style.getPropertyValue('--n')).toBe('19')
})

test('places a piece outline by its grid box, not by pixels', () => {
  const game = makeGame()
  game.players['1'].board.pieces = [{ topLeft: [1, 0], width: 2, height: 1, owner: 1 }]

  const { container } = render(<Board game={game} />)

  expect(box(container.querySelector('.piece-outline'))).toEqual({ r: '1', c: '0', w: '2', h: '1' })
})

test('places a vertical wall on the column boundary and a horizontal one on the row boundary', () => {
  const game = makeGame()
  game.houseRules.walls = {
    enabled: true,
    edges: [
      [[0, 1], [0, 2]],
      [[1, 0], [2, 0]],
    ],
  }

  const { container } = render(<Board game={game} />)

  const [vertical, horizontal] = container.querySelectorAll<HTMLElement>('.wall')
  expect(vertical).toHaveClass('wall-v')
  expect(box(vertical)).toMatchObject({ r: '0', c: '2' })
  expect(horizontal).toHaveClass('wall-h')
  expect(box(horizontal)).toMatchObject({ r: '2', c: '0' })
})

test.each(['legal', 'danger', 'pending'] as const)('renders the preview box with the %s class for that previewKind', (kind) => {
  const { container } = render(<Board game={makeGame()} previewTopLeft={[0, 0]} previewDims={[1, 1]} previewKind={kind} />)

  expect(container.querySelector('.preview')).toHaveClass(kind)
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

test('marks only the last-placed piece outline with the last class', () => {
  const game = makeGame()
  game.players['1'].board.pieces = [{ topLeft: [0, 0], width: 2, height: 1, owner: 1 }]
  game.players['2'].board.pieces = [{ topLeft: [2, 2], width: 1, height: 1, owner: 2 }]

  const { container } = render(<Board game={game} lastPlaced={[2, 2]} />)

  const outlines = container.querySelectorAll('.piece-outline')
  expect(container.querySelectorAll('.piece-outline.last')).toHaveLength(1)
  expect(outlines[1]).toHaveClass('last')
})
