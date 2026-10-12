import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../dev/fixtures/gameFixtures'
import { Board } from './Board'

test('renders one cell per board square', () => {
  const { container } = render(<Board game={makeGame()} />)
  expect(container.querySelectorAll('.board-cell')).toHaveLength(9)
})

test('exposes the grid as an accessible role with a size label', () => {
  render(<Board game={makeGame()} />)
  expect(screen.getByRole('group', { name: '3×3 board' })).toBeInTheDocument()
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

test('drops the special-cell marker once a piece has captured it', () => {
  const game = makeGame()
  game.houseRules.prize = { enabled: true, cells: [[0, 0]], points: 5 }
  game.players['1'].board.pieces = [{ topLeft: [0, 0], width: 1, height: 1, owner: 1 }]

  const { container } = render(<Board game={game} />)

  const cell = container.querySelector('[data-cell="0,0"]')
  expect(cell).toHaveClass('p1-fill')
  expect(cell).not.toHaveClass('prize')
})

test.each(['prize', 'pitfall', 'steal'] as const)(
  'rings a %s cell captured by the most recent placement, and only that one',
  (kind) => {
    const game = makeGame()
    game.houseRules[kind] = { enabled: true, cells: [[0, 0], [2, 2]], points: 5 }
    game.players['1'].board.pieces = [
      { topLeft: [2, 2], width: 1, height: 1, owner: 1 },
      { topLeft: [0, 0], width: 1, height: 1, owner: 1 },
    ]

    const { container } = render(<Board game={game} lastPlaced={[0, 0]} />)

    expect(container.querySelector('.capture-ring[data-cell="0,0"]')).toBeInTheDocument()
    expect(container.querySelector('.capture-ring[data-cell="2,2"]')).not.toBeInTheDocument()
  },
)

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

test.each([
  [1, 'var(--p1)'],
  [2, 'var(--p2)'],
] as const)("tints the legal-move layers with the mover's colour on player %i's turn", (currentPlayerId, colour) => {
  const game = makeGame()
  game.turn.currentPlayerId = currentPlayerId
  const { container } = render(<Board game={game} />)

  expect(container.querySelector<HTMLElement>('.board')!.style.getPropertyValue('--mover')).toBe(colour)
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

test("marks each player's starting corner until they place a piece", () => {
  const game = makeGame()

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('[data-cell="0,0"]')).toHaveClass('start-p1')
  expect(container.querySelector('[data-cell="2,2"]')).toHaveClass('start-p2')
  expect(container.querySelectorAll('.start-p1, .start-p2')).toHaveLength(2)
})

test('drops a start marker once that player has a piece, and keeps the other', () => {
  const game = makeGame()
  game.players['1'].board.pieces = [{ topLeft: [0, 0], width: 2, height: 1, owner: 1 }]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('.start-p1')).not.toBeInTheDocument()
  expect(container.querySelector('[data-cell="2,2"]')).toHaveClass('start-p2')
})

test('hatches a self-enclosed empty region in the enclosing player\'s color', () => {
  const game = makeGame({ board: { size: 5, skipLimit: 5 } })
  game.houseRules.selfEnclosedPenalty = { enabled: true }
  // Center cell (2,2) is surrounded on all 4 sides by player 1, never touching the board edge.
  game.players['1'].board.pieces = [
    { topLeft: [1, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [3, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 1], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 3], width: 1, height: 1, owner: 1 },
  ]

  const { container } = render(<Board game={game} />)

  const hatch = container.querySelector('.enclosed-hatch[data-cell="2,2"]')
  expect(hatch).toBeInTheDocument()
  expect(hatch).toHaveClass('p1')
})

test('does not hatch an empty region that touches the board edge', () => {
  const game = makeGame({ board: { size: 3, skipLimit: 5 } })
  game.houseRules.selfEnclosedPenalty = { enabled: true }
  // (0,0) is empty and borders player 1 on one side, but it's a corner cell - touches the edge.
  game.players['1'].board.pieces = [{ topLeft: [0, 1], width: 1, height: 1, owner: 1 }]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('.enclosed-hatch')).not.toBeInTheDocument()
})

test('does not hatch an empty region bordered by both players', () => {
  const game = makeGame({ board: { size: 5, skipLimit: 5 } })
  game.houseRules.selfEnclosedPenalty = { enabled: true }
  game.players['1'].board.pieces = [
    { topLeft: [1, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [3, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 1], width: 1, height: 1, owner: 1 },
  ]
  game.players['2'].board.pieces = [{ topLeft: [2, 3], width: 1, height: 1, owner: 2 }]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('.enclosed-hatch')).not.toBeInTheDocument()
})

test('a wall excludes the far side from the enclosing-owner check', () => {
  const game = makeGame({ board: { size: 5, skipLimit: 5 } })
  game.houseRules.selfEnclosedPenalty = { enabled: true }
  game.houseRules.walls = { enabled: true, edges: [[[2, 2], [2, 3]]] }
  game.players['1'].board.pieces = [
    { topLeft: [1, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [3, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 1], width: 1, height: 1, owner: 1 },
  ]
  // Without the wall, this player 2 piece would make the region two-owner and disqualify it.
  game.players['2'].board.pieces = [{ topLeft: [2, 3], width: 1, height: 1, owner: 2 }]

  const { container } = render(<Board game={game} />)

  const hatch = container.querySelector('.enclosed-hatch[data-cell="2,2"]')
  expect(hatch).toBeInTheDocument()
  expect(hatch).toHaveClass('p1')
})

test('does not hatch when the self-enclosed-penalty house rule is disabled', () => {
  const game = makeGame({ board: { size: 5, skipLimit: 5 } })
  game.houseRules.selfEnclosedPenalty = { enabled: false }
  game.players['1'].board.pieces = [
    { topLeft: [1, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [3, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 1], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 3], width: 1, height: 1, owner: 1 },
  ]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('.enclosed-hatch')).not.toBeInTheDocument()
})

test('an obstacle excludes the far side from the enclosing-owner check, same as a wall', () => {
  const game = makeGame({ board: { size: 5, skipLimit: 5 } })
  game.houseRules.selfEnclosedPenalty = { enabled: true }
  game.houseRules.obstacles = { enabled: true, cells: [[2, 3]] }
  game.players['1'].board.pieces = [
    { topLeft: [1, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [3, 2], width: 1, height: 1, owner: 1 },
    { topLeft: [2, 1], width: 1, height: 1, owner: 1 },
  ]

  const { container } = render(<Board game={game} />)

  expect(container.querySelector('.enclosed-hatch[data-cell="2,2"]')).toBeInTheDocument()
})
