import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../dev/fixtures/gameFixtures'
import type { GameState } from '../hooks/useGameSocket'
import { PlayingScreen } from './PlayingScreen'
import { keyboardState, makeState, renderRerenderable, renderScreen, renderVsBot, specialRules } from '../dev/testUtils/playingScreenHarness'

test.each([
  ['awaitingRoll', ['Roll']],
  ['choosingPlacement', ['Rotate']],
  ['skipped', ['Skip']],
] as const)('only the applicable action button is shown in the action row (%s)', (turnState, shown) => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

  const names = within(document.querySelector('.rail-actions') as HTMLElement)
    .getAllByRole('button')
    .map((b) => b.firstChild!.textContent!.trim())
  expect(names).toEqual([...shown])
})

test('clicking a legal cell while choosing placement sends the place action', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )

  fireEvent.pointerUp(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

test('Rotate swaps the orientation used for placement', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [
          { width: 2, height: 1, topLefts: [[0, 0]] },
          { width: 1, height: 2, topLefts: [[2, 2]] },
        ],
      },
    }),
  )

  fireEvent.click(screen.getByRole('button', { name: 'Rotate' }))
  fireEvent.pointerUp(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="3,2"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [2, 2], width: 1, height: 2 })
})

test('the r key rotates, once per press and not on auto-repeat', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [
          { width: 2, height: 1, topLefts: [[0, 0]] },
          { width: 1, height: 2, topLefts: [[2, 2]] },
        ],
      },
    }),
  )

  fireEvent.keyDown(window, { key: 'r' })
  fireEvent.keyDown(window, { key: 'r', repeat: true })
  fireEvent.pointerUp(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="3,2"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [2, 2], width: 1, height: 2 })
})

test('marks every cell any legal placement of the current orientation would cover as coverable', () => {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )
  const grid = screen.getByRole('group', { name: / board$/ })

  expect(grid.querySelector('[data-cell="0,0"]')).toHaveClass('coverable')
  expect(grid.querySelector('[data-cell="0,1"]')).toHaveClass('coverable')
  expect(grid.querySelector('[data-cell="1,0"]')).not.toHaveClass('coverable')
})

test('hovering an illegal cell shows the preview in the danger state', () => {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )

  fireEvent.mouseEnter(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="4,4"]')!)

  expect(screen.getByRole('group', { name: / board$/ }).querySelector('.preview')).toHaveClass('danger')
})

test('touch: two taps on the same cell are needed to place', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )
  const cell = screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="0,0"]')!

  fireEvent.pointerUp(cell, { pointerType: 'touch' })
  expect(sendAction).not.toHaveBeenCalled()

  fireEvent.pointerUp(cell, { pointerType: 'touch' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

// A browser follows a tap with compatibility mouse events, so the cell just tapped is also "hovered" before the second tap lands.
test('touch: the mouseover a browser sends after a tap does not undo the first tap', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )
  const cell = screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="0,0"]')!

  fireEvent.pointerUp(cell, { pointerType: 'touch' })
  fireEvent.mouseOver(cell)
  fireEvent.pointerUp(cell, { pointerType: 'touch' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

const botPlacementTurn = {
  recentTurns: [],
  currentPlayerId: 2,
  turnState: 'choosingPlacement' as const,
  lastRoll: [2, 1] as [number, number],
  legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] as [number, number][] }],
}

test("on the bot's turn, hovering shows no preview or coverable overlay and tapping places nothing", () => {
  const sendAction = renderVsBot(makeState({ board: { size: 5, skipLimit: 5 }, turn: botPlacementTurn }))
  const grid = screen.getByRole('group', { name: / board$/ })

  fireEvent.mouseEnter(grid.querySelector('[data-cell="0,0"]')!)
  fireEvent.pointerUp(grid.querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(grid.querySelector('.preview')).not.toBeInTheDocument()
  expect(grid.querySelector('.coverable')).not.toBeInTheDocument()
  expect(sendAction).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: 'Rotate' })).not.toBeInTheDocument()
})

test("on the human's turn against a bot, placement still works", () => {
  const sendAction = renderVsBot(makeState({ board: { size: 5, skipLimit: 5 }, turn: { ...botPlacementTurn, currentPlayerId: 1 } }))

  fireEvent.pointerUp(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

function withPieces(p1: [number, number][], p2: [number, number][]): GameState {
  const state = makeState({ board: { size: 6, skipLimit: 5 } })
  state.game.players['1'].board.pieces = p1.map((topLeft) => ({ topLeft, width: 1, height: 1, owner: 1 }))
  state.game.players['2'].board.pieces = p2.map((topLeft) => ({ topLeft, width: 1, height: 1, owner: 2 }))
  return state
}

const outlineAt = (row: number, col: number) => {
  const style = document.querySelector<HTMLElement>('.piece-outline.last')?.style
  return style?.getPropertyValue('--r') === String(row) && style?.getPropertyValue('--c') === String(col)
}

test('outlines the piece that was just placed, and keeps it through a skip', () => {
  const update = renderRerenderable(withPieces([[0, 0]], [[5, 5]]))
  expect(document.querySelector('.piece-outline.last')).not.toBeInTheDocument()

  update(withPieces([[0, 0], [0, 1]], [[5, 5]]))
  expect(document.querySelectorAll('.piece-outline.last')).toHaveLength(1)
  expect(outlineAt(0, 1)).toBe(true)

  update(withPieces([[0, 0], [0, 1]], [[5, 5]]))
  expect(outlineAt(0, 1)).toBe(true)
})

test("moves the last-placed outline to the opponent's next piece", () => {
  const update = renderRerenderable(withPieces([[0, 0]], [[5, 5]]))
  update(withPieces([[0, 0], [0, 1]], [[5, 5]]))
  update(withPieces([[0, 0], [0, 1]], [[5, 5], [5, 4]]))

  expect(document.querySelectorAll('.piece-outline.last')).toHaveLength(1)
  expect(outlineAt(5, 4)).toBe(true)
})

const hoverState = () =>
  makeState({
    board: { size: 5, skipLimit: 5 },
    turn: { recentTurns: [],
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 1],
      legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
    },
  })

test('hovering an illegal spot explains why in the status line', () => {
  renderScreen(hoverState())

  fireEvent.mouseOver(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="4,4"]')!)

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 2 wide × 1 tall — your first piece must cover your starting corner')
})

test('hovering a legal spot shows no reason', () => {
  renderScreen(hoverState())

  fireEvent.mouseOver(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="0,0"]')!)

  expect(screen.getByTestId('turn-status')).toHaveTextContent(/^Player 1: place 2 wide × 1 tall$/)
})

test('the board is a tab stop while a placement can be made', () => {
  renderScreen(keyboardState())
  expect(screen.getByRole('group', { name: / board$/ })).toHaveAttribute('tabindex', '0')
})

test('the board stays a tab stop when no placement is due, and its keys do nothing then', () => {
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))
  const board = screen.getByRole('group', { name: / board$/ })
  expect(board).toHaveAttribute('tabindex', '0')

  fireEvent.focus(board)
  fireEvent.keyDown(board, { key: 'ArrowRight' })
  fireEvent.keyDown(board, { key: 'Enter' })

  expect(document.querySelector('.preview')).not.toBeInTheDocument()
  expect(sendAction).not.toHaveBeenCalled()
})

test('keyboard focus stays on the board between turns, and the next placement starts on the first legal spot', () => {
  const props = { error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const { rerender } = render(<PlayingScreen state={keyboardState()} {...props} />)
  const board = screen.getByRole('group', { name: / board$/ })
  board.focus()

  rerender(<PlayingScreen state={makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } })} {...props} />)
  expect(board).toHaveFocus()

  rerender(<PlayingScreen state={keyboardState()} {...props} />)
  expect(board).toHaveFocus()
  expect(document.querySelector('.preview.legal')).toBeInTheDocument()
})

test('focusing the board puts the piece on the first legal spot', () => {
  renderScreen(keyboardState())

  fireEvent.focus(screen.getByRole('group', { name: / board$/ }))

  const preview = document.querySelector<HTMLElement>('.preview.legal')!
  expect(preview.style.getPropertyValue('--c')).toBe('0')
  expect(preview.style.getPropertyValue('--r')).toBe('0')
})

test('arrow keys move the piece and Enter places it', () => {
  const sendAction = renderScreen(keyboardState())
  const grid = screen.getByRole('group', { name: / board$/ })

  fireEvent.focus(grid)
  fireEvent.keyDown(grid, { key: 'ArrowRight' })
  expect(document.querySelector<HTMLElement>('.preview.legal')!.style.getPropertyValue('--c')).toBe('1')

  fireEvent.keyDown(grid, { key: 'Enter' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 1], width: 2, height: 1 })
})

test('moving onto an illegal spot explains why, and Enter does not place', () => {
  const sendAction = renderScreen(keyboardState())
  const grid = screen.getByRole('group', { name: / board$/ })

  fireEvent.focus(grid)
  fireEvent.keyDown(grid, { key: 'ArrowDown' })

  expect(document.querySelector('.preview.danger')).toBeInTheDocument()
  expect(screen.getByTestId('turn-status')).toHaveTextContent('your first piece must cover your starting corner')
  fireEvent.keyDown(grid, { key: 'Enter' })
  expect(sendAction).not.toHaveBeenCalled()
})

test('the board explains its keys to assistive tech', () => {
  renderScreen(keyboardState())

  const help = document.getElementById(screen.getByRole('group', { name: / board$/ }).getAttribute('aria-describedby')!.split(' ')[0]!)
  expect(help).toHaveTextContent('Arrows move, N next, Enter places, R rotates')
})

test('the placement keys are visible under the board, not only announced', () => {
  renderScreen(keyboardState())

  expect(screen.getByText('Arrows move, N next, Enter places, R rotates')).not.toHaveClass('visually-hidden')
})

test('the key hint under the board is blank on the roll turn and on the bot\'s turn', () => {
  const roll = makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } })
  const { unmount } = render(<PlayingScreen state={roll} error={null} sendAction={vi.fn()} onOpenSettings={vi.fn()} onNewGame={vi.fn()} />)
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
  unmount()

  renderScreen(roll, vi.fn(), null, vi.fn(), 1)
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test('a blank key hint holds a non-breaking space, so the line keeps its height and the board never jumps', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(document.getElementById('board-help')!.textContent).toBe('\u00A0')
})

test('the key hint under the board is blank on a dead roll, the status line carries the key', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test.each([
  ['awaitingRoll', 'Roll', 'd'],
  ['choosingPlacement', 'Rotate', 'r'],
  ['skipped', 'Skip', 's'],
] as const)('%s: the %s button exposes its keyboard shortcut to assistive tech', (turnState, name, key) => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByRole('button', { name })).toHaveAttribute('aria-keyshortcuts', key)
})

test.each([
  ['awaitingRoll', 'Roll', 'D'],
  ['choosingPlacement', 'Rotate', 'R'],
  ['skipped', 'Skip', 'S'],
] as const)('%s: the %s button carries a hidden %s key chip for the held-Shift cue', (turnState, name, key) => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

  const chip = screen.getByRole('button', { name }).querySelector('kbd.key-badge')
  expect(chip?.textContent).toBe(key)
  expect(chip).toHaveAttribute('aria-hidden', 'true')
})

test('the placement hint points at the starting corner first, then at the adjacency rule once a piece is down', () => {
  const state = keyboardState()
  const update = renderRerenderable(state)
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 2 wide × 1 tall — your first piece must cover your starting corner')

  const placed = keyboardState()
  placed.game.players['1'].board.pieces = [{ topLeft: [0, 0], width: 2, height: 1, owner: 1 }]
  update(placed)

  expect(screen.getByTestId('turn-status')).toHaveTextContent(/^Player 1: place 2 wide × 1 tall — must share an edge with your territory$/)
})

function placingOnSpecialBoard(rules: Parameters<typeof specialRules>[0]) {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: { recentTurns: [],
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 2],
        legalPlacements: [{ width: 2, height: 2, topLefts: [[0, 0]] }],
      },
      houseRules: specialRules(rules),
    }),
  )
  fireEvent.mouseEnter(screen.getByRole('group', { name: / board$/ }).querySelector('[data-cell="0,0"]')!)
}

test('a legal preview over a special cell ends the status line with what it would trigger', () => {
  placingOnSpecialBoard({ pitfall: { enabled: true, cells: [[1, 1]], points: 10 } })

  expect(screen.getByTestId('turn-status').textContent).toMatch(/ place 2 wide × 2 tall — covers Pitfall \(−10\)$/)
})

test('a preview over several special cells lists the kinds in rule order, not in board order', () => {
  // The Steal cell comes first when scanning the board row by row, the Pitfall cell second.
  placingOnSpecialBoard({
    steal: { enabled: true, cells: [[0, 1]], points: 10 },
    pitfall: { enabled: true, cells: [[1, 1]], points: 10 },
  })

  expect(screen.getByTestId('turn-status').textContent).toMatch(/ — covers Pitfall \(−10\), Steal \(±10\)$/)
})

test('a legal preview that covers no special cell adds nothing to the status line', () => {
  placingOnSpecialBoard({ pitfall: { enabled: true, cells: [[4, 4]], points: 10 } })

  expect(screen.getByTestId('turn-status').textContent).not.toMatch(/covers/)
})

test('a special cell of a rule that is off is not named', () => {
  placingOnSpecialBoard({ pitfall: { enabled: false, cells: [[1, 1]], points: 10 } })

  expect(screen.getByTestId('turn-status').textContent).not.toMatch(/covers/)
})

test('the piece position is announced as the keyboard moves it', () => {
  renderScreen(keyboardState())
  const board = screen.getByRole('group', { name: / board$/ })

  fireEvent.focus(board)
  expect(screen.getByTestId('cursor-position')).toHaveTextContent('Row 1, column 1, 2 empty cells')
  expect(screen.getByTestId('cursor-position')).toHaveAttribute('aria-live', 'polite')
  fireEvent.keyDown(board, { key: 'ArrowRight' })
  expect(screen.getByTestId('cursor-position')).toHaveTextContent('Row 1, column 2, 2 empty cells')
})

test('a mouse hover is read once, by the status line, not also as a position', () => {
  renderScreen(keyboardState())
  const board = screen.getByRole('group', { name: / board$/ })

  fireEvent.mouseOver(board.querySelector('[data-cell="0,0"]')!)

  expect(screen.getByTestId('cursor-position')).toBeEmptyDOMElement()
})

test('the position is announced again once the keyboard takes over from the mouse', () => {
  renderScreen(keyboardState())
  const board = screen.getByRole('group', { name: / board$/ })

  fireEvent.mouseOver(board.querySelector('[data-cell="0,0"]')!)
  fireEvent.keyDown(board, { key: 'ArrowRight' })

  expect(screen.getByTestId('cursor-position')).toHaveTextContent(/^Row \d+, column \d+, /)
})

test('no position is announced before the piece is on the board', () => {
  renderScreen(keyboardState())
  expect(screen.getByTestId('cursor-position')).toBeEmptyDOMElement()
})

test('the board summary names each player\'s pieces and cells, and the obstacles and walls', () => {
  const base = makeGame()
  const player = (id: '1' | '2', pieces: { topLeft: [number, number]; width: number; height: number; owner: number }[], area: number) => ({
    ...base.players[id],
    board: { ...base.players[id].board, pieces },
    score: { ...base.players[id].score, totalArea: area },
  })
  const state = makeState({
    turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [2, 1], legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }] },
    players: {
      '1': player('1', [{ topLeft: [0, 0], width: 2, height: 3, owner: 1 }, { topLeft: [0, 2], width: 1, height: 1, owner: 1 }], 7),
      '2': player('2', [], 0),
    },
    houseRules: { ...base.houseRules, obstacles: { enabled: true, cells: [[5, 5], [5, 6]] }, walls: { enabled: true, edges: [[[1, 1], [1, 2]]] } },
  })
  renderScreen(state)

  const describedBy = screen.getByRole('group', { name: / board$/ }).getAttribute('aria-describedby')!.split(' ')
  expect(describedBy).toContain('board-summary')
  const summary = document.getElementById('board-summary')!
  expect(summary).toHaveClass('visually-hidden')
  expect(summary).toHaveTextContent('Player 1: 2 pieces, 7 cells. Player 2: 0 pieces, 0 cells. 2 obstacle cells. 1 wall.')
})
