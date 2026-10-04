import { readFileSync } from 'node:fs'
import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, onTestFinished, test, vi } from 'vitest'
import { makeGame } from '../testUtils/gameFixtures'
import type { GameError, GameState } from '../useGameSocket'
import { PlayingScreen } from './PlayingScreen'

function makeState(overrides: Parameters<typeof makeGame>[0] = {}): GameState {
  return { game: makeGame(overrides), series: null }
}

function renderScreen(
  state: GameState | null,
  sendAction = vi.fn(),
  error: GameError | null = null,
  onNewGame = vi.fn(),
  botSeat?: number,
) {
  render(
    <PlayingScreen
      state={state}
      error={error}
      sendAction={sendAction}
      onOpenSettings={vi.fn()}
      onNewGame={onNewGame}
      botSeat={botSeat}
    />,
  )
  return sendAction
}

test('renders nothing game-specific before the first state broadcast arrives', () => {
  renderScreen(null)
  expect(screen.getByRole('button', { name: 'Menu' })).toBeInTheDocument()
  expect(screen.queryByRole('grid')).not.toBeInTheDocument()
})

test('highlights the current player in the turn indicator', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByText('Player 1').closest('.player')).not.toHaveClass('current')
  expect(screen.getByText('Player 2').closest('.player')).toHaveClass('current')
})

test('shows a Roll button while awaiting a roll, which sends the roll action', () => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
  expect(sendAction).toHaveBeenCalledWith({ type: 'roll' })
})

test('pressing d rolls while awaiting a roll', () => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'roll' })
})

test('pressing d does nothing once a roll is already showing', () => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [2, 5], legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })
  expect(sendAction).not.toHaveBeenCalled()
})

test('shows the last roll as dice once past awaitingRoll, with Roll hidden', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [2, 5], legalPlacements: [] } }))

  const dice = screen.getByText('2').closest('.dice')
  expect(dice).toContainElement(screen.getByText('5'))
  expect(screen.queryByRole('button', { name: 'Roll' })).not.toBeInTheDocument()
})

test('shows no dice while awaiting a roll', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.queryByRole('img', { name: /rolled/i })).not.toBeInTheDocument()
})

test.each([
  ['awaitingRoll', ['Roll']],
  ['choosingPlacement', ['Rotate']],
  ['skipped', ['Skip']],
] as const)('only the applicable action button and Menu are shown (%s)', (turnState, shown) => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

  const names = within(document.querySelector('.toolbar-actions') as HTMLElement)
    .getAllByRole('button')
    .map((b) => b.firstChild!.textContent!.trim())
  expect(names).toEqual([...shown, 'Menu'])
})

test('clicking a legal cell while choosing placement sends the place action', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: {
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )

  fireEvent.pointerUp(screen.getByRole('grid').querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

test('Rotate swaps the orientation used for placement', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: {
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
  fireEvent.pointerUp(screen.getByRole('grid').querySelector('[data-cell="3,2"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [2, 2], width: 1, height: 2 })
})

test('marks every cell any legal placement of the current orientation would cover as coverable', () => {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: {
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )
  const grid = screen.getByRole('grid')

  expect(grid.querySelector('[data-cell="0,0"]')).toHaveClass('coverable')
  expect(grid.querySelector('[data-cell="0,1"]')).toHaveClass('coverable')
  expect(grid.querySelector('[data-cell="1,0"]')).not.toHaveClass('coverable')
})

test('hovering an illegal cell shows the preview in the danger state', () => {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: {
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )

  fireEvent.mouseEnter(screen.getByRole('grid').querySelector('[data-cell="4,4"]')!)

  expect(screen.getByRole('grid').querySelector('.preview')).toHaveClass('danger')
})

test('touch: two taps on the same cell are needed to place', () => {
  const sendAction = renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: {
        currentPlayerId: 1,
        turnState: 'choosingPlacement',
        lastRoll: [2, 1],
        legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
      },
    }),
  )
  const cell = screen.getByRole('grid').querySelector('[data-cell="0,0"]')!

  fireEvent.pointerUp(cell, { pointerType: 'touch' })
  expect(sendAction).not.toHaveBeenCalled()

  fireEvent.pointerUp(cell, { pointerType: 'touch' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

test('shows a Skip button when the turn was skipped, which sends the skip action', () => {
  const sendAction = renderScreen(
    makeState({ turn: { currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }),
  )

  fireEvent.click(screen.getByRole('button', { name: 'Skip' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test("shows each player's total score in their header slot", () => {
  const game = makeGame()
  game.players['1'].score.totalScore = 12
  game.players['2'].score.totalScore = 7
  renderScreen({ game, series: null })

  const p1 = screen.getByText('Player 1').closest('.player') as HTMLElement
  const p2 = screen.getByText('Player 2').closest('.player') as HTMLElement
  expect(within(p1).getByText('12')).toHaveClass('score')
  expect(within(p2).getByText('7')).toHaveClass('score')
})

test("each header score is read out as points, not a bare number", () => {
  const game = makeGame()
  game.players['1'].score.totalScore = 12
  renderScreen({ game, series: null })

  const p1 = screen.getByText('Player 1').closest('.player') as HTMLElement
  expect(p1).toHaveTextContent('12 points')
})

test("shows both players' skip streaks against the skip limit at the same time", () => {
  const game = makeGame({ board: { size: 3, skipLimit: 5 } })
  game.players['1'].board.consecutiveSkips = 2
  game.players['2'].board.consecutiveSkips = 0
  renderScreen({ game, series: null })

  const p1 = screen.getByText('Player 1').closest('.player') as HTMLElement
  const p2 = screen.getByText('Player 2').closest('.player') as HTMLElement
  expect(within(p1).getByText('2/5 skips')).toHaveClass('streak')
  expect(within(p2).getByText('0/5 skips')).toHaveClass('streak')
})

test('a player one skip from the limit gets the last-skip mark on their streak, the other does not', () => {
  const game = makeGame({ board: { size: 3, skipLimit: 5 } })
  game.players['1'].board.consecutiveSkips = 4
  game.players['2'].board.consecutiveSkips = 2
  renderScreen({ game, series: null })

  const p1 = screen.getByText('Player 1').closest('.player') as HTMLElement
  const p2 = screen.getByText('Player 2').closest('.player') as HTMLElement
  expect(within(p1).getByText('4/5 skips')).toHaveClass('last-skip')
  expect(within(p2).getByText('2/5 skips')).not.toHaveClass('last-skip')
})

test("groups each player's dot with their name, and orders the scoreline skips before score", () => {
  const game = makeGame()
  game.players['1'].score.totalScore = 12
  renderScreen({ game, series: null })

  const p1 = screen.getByText('Player 1').closest('.player') as HTMLElement
  const playerId = screen.getByText('Player 1').closest('.player-id') as HTMLElement
  expect(playerId).not.toBeNull()
  expect(playerId.querySelector('.dot')).toBeInTheDocument()

  const scoreline = p1.querySelector('.scoreline') as HTMLElement
  const [first, second] = Array.from(scoreline.children)
  expect(first).toHaveClass('streak')
  expect(second).toHaveClass('score')
})

test.each([
  ['illegalPlacement', 'That piece can’t go there — try another spot.'],
  ['invalidAction', 'You can’t do that right now — finish your current step.'],
  ['protocolVersionMismatch', 'This game is out of date — reload the page.'],
  ['illegalWildcardValue', 'That number can’t be placed — pick another.'],
  ['malformedMessage', 'Something went wrong — try again.'],
] as const)('shows friendly toast text for a %s server error', (reason, text) => {
  renderScreen(makeState(), vi.fn(), { reason, message: 'raw server text' })

  expect(screen.getByRole('status')).toHaveTextContent(text)
})

afterEach(() => vi.useRealTimers())

test('the error toast auto-dismisses after 4 seconds', () => {
  vi.useFakeTimers()
  renderScreen(makeState(), vi.fn(), { reason: 'illegalPlacement', message: 'x' })

  act(() => vi.advanceTimersByTime(3999))
  expect(screen.getByRole('status')).not.toBeEmptyDOMElement()

  act(() => vi.advanceTimersByTime(1))
  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

test('a newer error replaces the toast and restarts the 4 second timer', () => {
  vi.useFakeTimers()
  const props = { state: makeState(), sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const { rerender } = render(<PlayingScreen {...props} error={{ reason: 'illegalPlacement', message: 'x' }} />)

  act(() => vi.advanceTimersByTime(3000))
  rerender(<PlayingScreen {...props} error={{ reason: 'invalidAction', message: 'y' }} />)
  expect(screen.getByRole('status')).toHaveTextContent('You can’t do that right now — finish your current step.')

  act(() => vi.advanceTimersByTime(3999))
  expect(screen.getByRole('status')).not.toBeEmptyDOMElement()
  act(() => vi.advanceTimersByTime(1))
  expect(screen.getByRole('status')).toBeEmptyDOMElement()

  rerender(<PlayingScreen {...props} error={{ reason: 'invalidAction', message: 'y' }} />)
  expect(screen.getByRole('status')).not.toBeEmptyDOMElement()
})

test("marks only the current player's slot with aria-current", () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByText('Player 1').closest('.player')).not.toHaveAttribute('aria-current')
  expect(screen.getByText('Player 2').closest('.player')).toHaveAttribute('aria-current', 'true')
})

test('the dice have an accessible name describing the roll', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 1], legalPlacements: [] } }))

  expect(screen.getByRole('img', { name: 'Player 1 rolled 3 and 1' })).toBeInTheDocument()
})

test('the error status region is mounted from the start and empty until an error arrives', () => {
  renderScreen(makeState())

  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

test('the Playing screen has a level-1 heading', () => {
  renderScreen(makeState())

  expect(screen.getByRole('heading', { level: 1, name: 'Playing' })).toBeInTheDocument()
})

test('the d hotkey does not roll while a modal dialog is open', () => {
  const sendAction = renderScreen(
    makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }),
  )
  const dialog = document.createElement('dialog')
  document.body.appendChild(dialog)
  dialog.showModal()

  fireEvent.keyDown(window, { key: 'd' })
  expect(sendAction).not.toHaveBeenCalled()

  dialog.close()
  fireEvent.keyDown(window, { key: 'd' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'roll' })
  dialog.remove()
})

const gameOverTurn = { currentPlayerId: 1, turnState: 'gameOver' as const, lastRoll: null, legalPlacements: [] }

test('game over shows a dialog with the end reason and the winner', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))

  const dialog = screen.getByRole('dialog')
  expect(within(dialog).getByText('board settled')).toBeInTheDocument()
  expect(within(dialog).getByRole('heading', { name: 'Player\u00a01 wins on score' })).toBeInTheDocument()
})

test('no game-over dialog while the game is in progress', () => {
  renderScreen(makeState())
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

test.each([
  ['playerBlocked', 2, 'Player 2 boxed in'],
  ['skipLimit', 1, 'Player 1 hit the skip limit (5 of 5)'],
  ['surrender', 2, 'Player 2 surrendered'],
] as const)('game over names the player for a %s ending', (reason, playerId, text) => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason, playerId, winner: 1 } }))
  expect(within(screen.getByRole('dialog')).getByText(text)).toBeInTheDocument()
})

test('a surrender win reads plain "wins", not "on score"', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'surrender', playerId: 2, winner: 1 } }))
  expect(within(screen.getByRole('dialog')).getByRole('heading', { name: 'Player\u00a01 wins' })).toBeInTheDocument()
})

test('game over reads "Tied" when there is no winner', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: null } }))
  expect(within(screen.getByRole('dialog')).getByRole('heading', { name: 'Tied' })).toBeInTheDocument()
})

test('a plain game over shows the final score as a group of both totals', () => {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: 5, totalScore: 5 }
  game.players['2'].score = { ...game.players['2'].score, totalArea: 4, totalScore: 4 }
  renderScreen({ game, series: null })

  expect(within(screen.getByRole('dialog')).getByRole('group', { name: 'Final score' })).toHaveTextContent('Player 15Player 24')
})

test('game over shows a Prize breakdown row, in points, when Prize is enabled', () => {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.houseRules.prize = { enabled: true, cells: [], points: 5 }
  game.players['1'].houseRules.prize.captured = 2
  game.players['2'].houseRules.prize.captured = 1
  renderScreen({ game, series: null })

  const table = within(screen.getByRole('dialog')).getByRole('table')
  const row = within(table).getByRole('row', { name: /Prize/ })
  expect([within(row).getByRole('rowheader').textContent, ...within(row).getAllByRole('cell').map((c) => c.textContent)]).toEqual([
    'Prize+5 per captured cell',
    '10',
    '5',
  ])
})

test('game over shows a Pitfall breakdown row, as a negative deduction, when Pitfall is enabled', () => {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.houseRules.pitfall = { enabled: true, cells: [], points: 10 }
  game.players['1'].houseRules.pitfall.captured = 1
  game.players['2'].houseRules.pitfall.captured = 0
  renderScreen({ game, series: null })

  const table = within(screen.getByRole('dialog')).getByRole('table')
  const row = within(table).getByRole('row', { name: /Pitfall/ })
  expect([within(row).getByRole('rowheader').textContent, ...within(row).getAllByRole('cell').map((c) => c.textContent)]).toEqual([
    'Pitfall−10 per captured cell',
    '−10',
    '0',
  ])
})

test('game over shows a Steal breakdown row, as each player\'s net swing, when Steal is enabled', () => {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.houseRules.steal = { enabled: true, cells: [], points: 10 }
  game.players['1'].houseRules.steal.captured = 2
  game.players['2'].houseRules.steal.captured = 1
  renderScreen({ game, series: null })

  const table = within(screen.getByRole('dialog')).getByRole('table')
  const row = within(table).getByRole('row', { name: /Steal/ })
  expect([within(row).getByRole('rowheader').textContent, ...within(row).getAllByRole('cell').map((c) => c.textContent)]).toEqual([
    'Steal±10 per capture, zero-sum',
    '10',
    '−10',
  ])
})

test('game over shows an Enclosure breakdown row, as a negative deduction of 1 per cell, when enabled', () => {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.houseRules.selfEnclosedPenalty = { enabled: true }
  game.players['1'].houseRules.selfEnclosedPenalty.cells = 3
  game.players['2'].houseRules.selfEnclosedPenalty.cells = 0
  renderScreen({ game, series: null })

  const table = within(screen.getByRole('dialog')).getByRole('table')
  const row = within(table).getByRole('row', { name: /Enclosure/ })
  expect([within(row).getByRole('rowheader').textContent, ...within(row).getAllByRole('cell').map((c) => c.textContent)]).toEqual([
    'Enclosure−1 per sealed-in cell',
    '−3',
    '0',
  ])
})

test('the game-over dialog offers New Game', () => {
  const onNewGame = vi.fn()
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }), vi.fn(), null, onNewGame)

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'New Game' }))

  expect(onNewGame).toHaveBeenCalledTimes(1)
})

function gameOverState() {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: 158, totalScore: 158 }
  game.players['2'].score = { ...game.players['2'].score, totalArea: 141, totalScore: 141 }
  return { game, series: null }
}

test('View Board hides the result dialog and pins a slim result bar over the board', () => {
  renderScreen(gameOverState())

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))

  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  const bar = screen.getByRole('region', { name: 'Game result' })
  expect(bar).toHaveTextContent('Player 1 wins on score')
  expect(bar).toHaveTextContent('158 – 141')
  expect(screen.getByRole('grid')).toBeInTheDocument()
})

test('Escape on the result dialog shows the board, and View Result brings the dialog back', () => {
  renderScreen(gameOverState())

  fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

  fireEvent.click(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'View Result' }))
  expect(screen.getByRole('dialog')).toBeInTheDocument()
  expect(screen.queryByRole('region', { name: 'Game result' })).not.toBeInTheDocument()
})

test('the result bar offers New Game', () => {
  const onNewGame = vi.fn()
  renderScreen(gameOverState(), vi.fn(), null, onNewGame)
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))

  fireEvent.click(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'New Game' }))

  expect(onNewGame).toHaveBeenCalledTimes(1)
})

test('game-over player names use a non-breaking space so they never wrap mid-name', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))
  expect(within(screen.getByRole('dialog')).getByRole('heading').textContent).toBe('Player\u00a01 wins on score')
})

const renderVsBot = (state: GameState) => renderScreen(state, vi.fn(), null, vi.fn(), 2)

const botPlacementTurn = {
  currentPlayerId: 2,
  turnState: 'choosingPlacement' as const,
  lastRoll: [2, 1] as [number, number],
  legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] as [number, number][] }],
}

test("on the bot's turn, hovering shows no preview or coverable overlay and tapping places nothing", () => {
  const sendAction = renderVsBot(makeState({ board: { size: 5, skipLimit: 5 }, turn: botPlacementTurn }))
  const grid = screen.getByRole('grid')

  fireEvent.mouseEnter(grid.querySelector('[data-cell="0,0"]')!)
  fireEvent.pointerUp(grid.querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(grid.querySelector('.preview')).not.toBeInTheDocument()
  expect(grid.querySelector('.coverable')).not.toBeInTheDocument()
  expect(sendAction).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: 'Rotate' })).not.toBeInTheDocument()
})

test("on the bot's turn the Roll button is hidden and d does not roll", () => {
  const sendAction = renderVsBot(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })

  expect(screen.queryByRole('button', { name: 'Roll' })).not.toBeInTheDocument()
  expect(sendAction).not.toHaveBeenCalled()
})

test("on the bot's turn the Skip button is hidden", () => {
  renderVsBot(makeState({ turn: { currentPlayerId: 2, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))
  expect(screen.queryByRole('button', { name: 'Skip' })).not.toBeInTheDocument()
})

test("on the human's turn against a bot, placement still works", () => {
  const sendAction = renderVsBot(makeState({ board: { size: 5, skipLimit: 5 }, turn: { ...botPlacementTurn, currentPlayerId: 1 } }))

  fireEvent.pointerUp(screen.getByRole('grid').querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

test('the turn status line is a polite live region that is re-read whole', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  const status = screen.getByTestId('turn-status')
  expect(status).toHaveAttribute('aria-live', 'polite')
  expect(status).toHaveAttribute('aria-atomic', 'true')
  expect(document.querySelector('.turn-announcer')).not.toBeInTheDocument()
})

test('there is no Replay button mid-game; Replay is only reachable from the game-over dialog', () => {
  renderScreen(makeState())
  expect(screen.queryByRole('button', { name: 'Replay' })).not.toBeInTheDocument()
})

test.each(['awaitingRoll', 'choosingPlacement', 'skipped'] as const)(
  'Menu sits in the trailing toolbar group while %s',
  (turnState) => {
    renderScreen(makeState({ turn: { currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

    expect(screen.getByRole('button', { name: 'Menu' }).parentElement).toHaveClass('toolbar-trailing')
  },
)

test('Menu stays in the trailing toolbar group once the game is over', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'gameOver', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByRole('button', { name: 'Menu' }).parentElement).toHaveClass('toolbar-trailing')
})

test('the turn status line tells the current player what to do: roll', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 2: roll (D)')
})

test('the turn status line names the rectangle to place, following Rotate', () => {
  renderScreen(
    makeState({
      board: { size: 5, skipLimit: 5 },
      turn: {
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

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 2 wide × 1 tall')
  fireEvent.click(screen.getByRole('button', { name: 'Rotate' }))
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 1 wide × 2 tall')
})

const deadRoll = (consecutiveSkips: number) => {
  const game = makeGame({ board: { size: 3, skipLimit: 5 }, turn: { currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } })
  game.players['1'].board.consecutiveSkips = consecutiveSkips
  return game
}

test('a dead roll names which skip this would be, against the limit', () => {
  renderScreen({ game: deadRoll(1), series: null })

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skip (S) · skip 2 of 5')
})

test('the skip cue follows the reroll wording, and the skip that reaches the limit says it ends the game', () => {
  const withReroll = (game: ReturnType<typeof deadRoll>) => {
    game.houseRules.reroll = { enabled: true, canReroll: true }
    return game
  }
  renderScreen({ game: withReroll(deadRoll(1)), series: null })
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move — skip (S), or reroll (E) · skip 2 of 5')

  cleanup()
  renderScreen({ game: withReroll(deadRoll(4)), series: null })
  expect(screen.getByTestId('turn-status')).toHaveTextContent('· skip 5 of 5 ends the game')
})

test('the turn status line says when a dead roll must be skipped', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skip (S)')
})

test("the turn status line shows the bot is playing on the bot's turn", () => {
  renderScreen(
    makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }),
    vi.fn(),
    null,
    vi.fn(),
    2,
  )

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 2 is playing…')
})

test('there is no turn status line once the game is over', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))

  expect(screen.queryByTestId('turn-status')).not.toBeInTheDocument()
})

const rolledState = (turnState: 'choosingPlacement' | 'awaitingRoll', lastRoll: [number, number] | null) =>
  makeState({ turn: { currentPlayerId: 1, turnState, lastRoll, legalPlacements: [] } })

function renderRerenderable(state: GameState) {
  const props = { error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const view = render(<PlayingScreen state={state} {...props} />)
  return (next: GameState) => view.rerender(<PlayingScreen state={next} {...props} />)
}

test('keeps the last roll on screen, marked as the last roll, once the next turn awaits a roll', () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  expect(screen.getByRole('img', { name: 'Player 1 rolled 3 and 5' })).toBeInTheDocument()

  update(rolledState('awaitingRoll', null))

  const dice = screen.getByRole('img', { name: 'Player 1’s last roll 3 and 5' })
  expect(dice).toHaveClass('stale')
  expect(dice).toHaveTextContent('P1 last')
})

// jsdom skips the imported stylesheet, so tests that assert computed style inject the real file.
function injectPlayingCss() {
  const style = document.createElement('style')
  style.textContent = readFileSync('src/screens/PlayingScreen.css', 'utf8')
  document.head.append(style)
  onTestFinished(() => style.remove())
}

test('the dice are border-box, so their 34px matches the buttons and the toolbar does not grow on the first roll', () => {
  injectPlayingCss()

  renderScreen(rolledState('choosingPlacement', [3, 5]))

  expect([...document.querySelectorAll('.die')].map((d) => getComputedStyle(d).boxSizing)).toEqual(['border-box', 'border-box'])
})

test('the last roll is marked by a dashed border and a one-line owner label, not by dimming its digits', () => {
  injectPlayingCss()
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  const dice = () => [...document.querySelectorAll('.die')].map((d) => getComputedStyle(d))

  expect(dice().map((c) => c.borderTopStyle)).not.toContain('dashed')

  update(rolledState('awaitingRoll', null))

  expect(dice().map((c) => c.borderTopStyle)).toEqual(['dashed', 'dashed'])
  expect([...dice(), getComputedStyle(document.querySelector('.dice .dot')!)].map((c) => c.opacity)).toEqual(['1', '1', '1'])
  expect(getComputedStyle(screen.getByText('P1 last')).whiteSpace).toBe('nowrap')
})

test('the winner’s score cell has a 4px top border and 4px less top padding, so the scoreboard keeps its height', () => {
  injectPlayingCss()

  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))

  const [winner, other] = [...document.querySelectorAll('.game-over-scoreboard > div')].map((d) => getComputedStyle(d))
  expect([winner.borderTopWidth, winner.borderTopStyle, winner.paddingTop]).toEqual(['4px', 'solid', '6px'])
  expect([other.borderTopWidth, other.paddingTop]).toEqual(['0px', '10px'])
})

test('the breakdown row note and the biggest-swing tag are 12px, and the story bolds only its margin', () => {
  injectPlayingCss()
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.houseRules.prize = { enabled: true, cells: [], points: 5 }
  game.houseRules.steal = { enabled: true, cells: [], points: 10 }
  game.players['1'].houseRules.prize.captured = 2
  game.players['1'].houseRules.steal.captured = 2
  game.players['1'].score = { ...game.players['1'].score, totalArea: 120, totalScore: 140 }
  game.players['2'].score = { ...game.players['2'].score, totalArea: 120, totalScore: 120 }
  renderScreen({ game, series: null })

  expect(getComputedStyle(screen.getByText('+5 per captured cell')).fontSize).toBe('12px')
  expect(getComputedStyle(screen.getByText('Biggest swing')).fontSize).toBe('12px')
  expect(getComputedStyle(screen.getByText('20 points')).fontWeight).toBe('600')
  expect(getComputedStyle(document.querySelector('.game-over-story')!).fontWeight).not.toBe('600')
})

test('the trailing total is 70% ink, so it clears 4.5:1 and still reads as the lower number', () => {
  injectPlayingCss()
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))

  const total = document.querySelector('.game-over-scoreboard .trail .n')!
  expect(getComputedStyle(total).color).toBe('color-mix(in srgb, var(--ink) 70%, transparent)')
})

test('a headline followed straight by the scoreboard keeps 18px below it', () => {
  injectPlayingCss()
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: null } }))

  expect(getComputedStyle(screen.getByRole('heading', { name: 'Tied' })).marginBottom).toBe('18px')
})

test('shows no dice before the first roll of the game', () => {
  renderScreen(rolledState('awaitingRoll', null))

  expect(screen.queryByRole('img', { name: /roll/i })).not.toBeInTheDocument()
})

test('a new roll replaces the dimmed last roll', () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  update(rolledState('awaitingRoll', null))
  update(rolledState('choosingPlacement', [1, 6]))

  expect(screen.getByRole('img', { name: 'Player 1 rolled 1 and 6' })).not.toHaveClass('stale')
  expect(screen.getByRole('img', { name: 'Player 1 rolled 1 and 6' })).not.toHaveTextContent('last')
  expect(screen.queryByRole('img', { name: /last roll/i })).not.toBeInTheDocument()
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
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 1],
      legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0]] }],
    },
  })

test('hovering an illegal spot explains why in the status line', () => {
  renderScreen(hoverState())

  fireEvent.mouseOver(screen.getByRole('grid').querySelector('[data-cell="4,4"]')!)

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 2 wide × 1 tall — your first piece must cover your starting corner')
})

test('hovering a legal spot shows no reason', () => {
  renderScreen(hoverState())

  fireEvent.mouseOver(screen.getByRole('grid').querySelector('[data-cell="0,0"]')!)

  expect(screen.getByTestId('turn-status')).toHaveTextContent(/^Player 1: place 2 wide × 1 tall$/)
})

const keyboardState = () =>
  makeState({
    board: { size: 5, skipLimit: 5 },
    turn: {
      currentPlayerId: 1,
      turnState: 'choosingPlacement',
      lastRoll: [2, 1],
      legalPlacements: [{ width: 2, height: 1, topLefts: [[0, 0], [0, 1]] }],
    },
  })

test('the board is keyboard-focusable only while a placement can be made', () => {
  renderScreen(keyboardState())
  expect(screen.getByRole('grid')).toHaveAttribute('tabindex', '0')
})

test('the board is not focusable while awaiting a roll', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))
  expect(screen.getByRole('grid')).not.toHaveAttribute('tabindex')
})

test('focusing the board puts the piece on the first legal spot', () => {
  renderScreen(keyboardState())

  fireEvent.focus(screen.getByRole('grid'))

  const preview = document.querySelector<HTMLElement>('.preview.legal')!
  expect(preview.style.getPropertyValue('--c')).toBe('0')
  expect(preview.style.getPropertyValue('--r')).toBe('0')
})

test('arrow keys move the piece and Enter places it', () => {
  const sendAction = renderScreen(keyboardState())
  const grid = screen.getByRole('grid')

  fireEvent.focus(grid)
  fireEvent.keyDown(grid, { key: 'ArrowRight' })
  expect(document.querySelector<HTMLElement>('.preview.legal')!.style.getPropertyValue('--c')).toBe('1')

  fireEvent.keyDown(grid, { key: 'Enter' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 1], width: 2, height: 1 })
})

test('moving onto an illegal spot explains why, and Enter does not place', () => {
  const sendAction = renderScreen(keyboardState())
  const grid = screen.getByRole('grid')

  fireEvent.focus(grid)
  fireEvent.keyDown(grid, { key: 'ArrowDown' })

  expect(document.querySelector('.preview.danger')).toBeInTheDocument()
  expect(screen.getByTestId('turn-status')).toHaveTextContent('your first piece must cover your starting corner')
  fireEvent.keyDown(grid, { key: 'Enter' })
  expect(sendAction).not.toHaveBeenCalled()
})

test('the board explains its keys to assistive tech', () => {
  renderScreen(keyboardState())

  const help = document.getElementById(screen.getByRole('grid').getAttribute('aria-describedby')!)
  expect(help).toHaveTextContent('Arrows move, N next legal spot, Enter places, R rotates')
})

test('the placement keys are visible under the board, not only announced', () => {
  renderScreen(keyboardState())

  expect(screen.getByText('Arrows move, N next legal spot, Enter places, R rotates')).not.toHaveClass('visually-hidden')
})

test('the key hint under the board is blank on the roll turn and on the bot\'s turn', () => {
  const roll = makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } })
  const { unmount } = render(<PlayingScreen state={roll} error={null} sendAction={vi.fn()} onOpenSettings={vi.fn()} onNewGame={vi.fn()} />)
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
  unmount()

  renderScreen(roll, vi.fn(), null, vi.fn(), 1)
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test('a blank key hint holds a non-breaking space, so the line keeps its height and the board never jumps', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(document.getElementById('board-help')!.textContent).toBe('\u00A0')
})

test('the key hint under the board is blank on a dead roll, the status line carries the key', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test.each([
  ['awaitingRoll', 'Roll', 'd'],
  ['choosingPlacement', 'Rotate', 'r'],
  ['skipped', 'Skip', 's'],
] as const)('%s: the %s button exposes its keyboard shortcut to assistive tech', (turnState, name, key) => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByRole('button', { name })).toHaveAttribute('aria-keyshortcuts', key)
})

test('pressing s skips a dead roll', () => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 's' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test('pressing s does nothing when the roll is playable', () => {
  const sendAction = renderScreen(keyboardState())

  fireEvent.keyDown(window, { key: 's' })

  expect(sendAction).not.toHaveBeenCalled()
})

test('the dice carry a dot in the color of the player who rolled them', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'choosingPlacement', lastRoll: [4, 2], legalPlacements: [] } }))

  const dice = screen.getByRole('img', { name: 'Player 2 rolled 4 and 2' })
  expect(dice).toHaveClass('p2')
  expect(dice.querySelector('.dot')).toBeInTheDocument()
})

test("a dimmed last roll keeps its roller's name and color through the next player's turn", () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))

  update(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  const dice = screen.getByRole('img', { name: 'Player 1’s last roll 3 and 5' })
  expect(dice).toHaveClass('p1')
  expect(dice.querySelector('.dot')).toBeInTheDocument()
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

test('the error toast hangs from the sticky header, so it follows the header height', () => {
  renderScreen(makeState(), vi.fn(), { reason: 'illegalPlacement', message: 'x' })

  const toast = screen.getByText(/can’t go there/)
  expect(toast.closest('.header')).toBeInTheDocument()
})

const wildcardState = ({
  editableIndex,
  legalValues,
  currentPlayerId = 1,
}: {
  editableIndex: 0 | 1
  legalValues: number[]
  currentPlayerId?: number
}) => {
  const state = makeState({ turn: { currentPlayerId, turnState: 'choosingWildcard', lastRoll: [4, 4], legalPlacements: [] } })
  state.game.houseRules.wildcard = { enabled: true, originalRoll: [4, 4], legalValues, editableIndex }
  return state
}

const pillNames = () => within(screen.getByRole('group', { name: 'Wildcard value' })).getAllByRole('button').map((b) => b.textContent)

test('choosing a wildcard shows the fixed die and a pill for each value 1-6, in place of the dice', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3, 4, 5, 6] }))

  expect(pillNames()).toEqual(['1', '2', '3', '4', '5', '6'])
  expect(screen.getByTestId('wildcard-fixed-die')).toHaveTextContent('4')
  expect(screen.queryByRole('img', { name: /rolled/i })).not.toBeInTheDocument()
})

test('the fixed die is exposed by name so a screen reader hears the number the pills pair with', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3] }))

  expect(screen.getByRole('img', { name: 'Fixed die 4' })).toBeInTheDocument()
})

test('values with no legal placement are disabled, not removed', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 3, 4, 6] }))

  const group = screen.getByRole('group', { name: 'Wildcard value' })
  for (const [name, enabled] of [['1', true], ['2', false], ['3', true], ['4', true], ['5', false], ['6', true]] as const) {
    const pill = within(group).getByRole('button', { name })
    if (enabled) expect(pill).toBeEnabled()
    else expect(pill).toBeDisabled()
  }
})

test('clicking a pill sends chooseWildcard with that value straight away', () => {
  const sendAction = renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 3, 4, 6] }))

  fireEvent.click(screen.getByRole('button', { name: '3' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'chooseWildcard', value: 3 })
})

test.each([0, 1] as const)('editableIndex %i: the pills take the wildcard die\'s slot', (editableIndex) => {
  renderScreen(wildcardState({ editableIndex, legalValues: [1, 2, 3, 4, 5, 6] }))

  const picker = screen.getByTestId('wildcard-fixed-die').parentElement!
  const isPillsFirst = picker.firstElementChild!.getAttribute('role') === 'group'
  expect(isPillsFirst).toBe(editableIndex === 0)
})

test('the wildcard turn status describes the pick and the key hint stays blank', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3] }))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: wildcard roll — pick the other die’s value')
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test('a wildcard roll where no value fits skips the picker and goes straight to Skip', () => {
  const state = makeState({ turn: { currentPlayerId: 1, turnState: 'skipped', lastRoll: [4, 4], legalPlacements: [] } })
  state.game.houseRules.wildcard = { enabled: true, originalRoll: [4, 4], legalValues: [], editableIndex: null }
  renderScreen(state)

  expect(screen.queryByRole('group', { name: 'Wildcard value' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled()
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skip (S)')
})

test("on the bot's turn a pending wildcard shows plain dice and no picker", () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3], currentPlayerId: 2 }), vi.fn(), null, vi.fn(), 2)

  expect(screen.queryByRole('group', { name: 'Wildcard value' })).not.toBeInTheDocument()
  expect(screen.getByRole('img', { name: /rolled 4 and 4/i })).toBeInTheDocument()
})

const rerollState = (canReroll: boolean, turnState: 'choosingPlacement' | 'skipped' | 'choosingWildcard' = 'choosingPlacement') => {
  const state = makeState({ turn: { currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } })
  state.game.houseRules.reroll = { enabled: true, canReroll }
  return state
}

test('there is no Reroll button when the house rule is off', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.queryByRole('button', { name: 'Reroll' })).not.toBeInTheDocument()
})

test('shows an enabled Reroll button with charges remaining, which sends the reroll action', () => {
  const sendAction = renderScreen(rerollState(true))

  fireEvent.click(screen.getByRole('button', { name: 'Reroll' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test('hides Reroll once charges are exhausted', () => {
  renderScreen(rerollState(false))

  expect(screen.queryByRole('button', { name: 'Reroll' })).not.toBeInTheDocument()
})

test('Reroll stays enabled alongside a forced Skip', () => {
  renderScreen(rerollState(true, 'skipped'))

  expect(screen.getByRole('button', { name: 'Reroll' })).toBeEnabled()
})

test('Reroll is available while choosing a wildcard value, and E rerolls', () => {
  const state = wildcardState({ editableIndex: 1, legalValues: [1, 2, 3] })
  state.game.houseRules.reroll = { enabled: true, canReroll: true }
  const sendAction = renderScreen(state)

  expect(screen.getByRole('button', { name: 'Reroll' })).toBeEnabled()
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: wildcard roll — pick the other die’s value, or reroll (E)')
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
  fireEvent.keyDown(window, { key: 'e' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test("on the bot's turn the Reroll button is hidden", () => {
  renderScreen(rerollState(true), vi.fn(), null, vi.fn(), 1)

  expect(screen.queryByRole('button', { name: 'Reroll' })).not.toBeInTheDocument()
})

test('Reroll exposes its keyboard shortcut to assistive tech', () => {
  renderScreen(rerollState(true))

  expect(screen.getByRole('button', { name: 'Reroll' })).toHaveAttribute('aria-keyshortcuts', 'e')
})

test('pressing e rerolls when charges remain', () => {
  const sendAction = renderScreen(rerollState(true))

  fireEvent.keyDown(window, { key: 'e' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test('pressing e does nothing once charges are exhausted', () => {
  const sendAction = renderScreen(rerollState(false))

  fireEvent.keyDown(window, { key: 'e' })

  expect(sendAction).not.toHaveBeenCalled()
})

test("appends each player's reroll charges to their skip streak, comma-joined", () => {
  const state = rerollState(true)
  state.game.players['1'].houseRules.reroll = { used: 1, limit: 3 }
  state.game.players['2'].houseRules.reroll = { used: 2, limit: 2 }
  renderScreen(state)

  const p1 = screen.getByText('Player 1').closest('.player') as HTMLElement
  const p2 = screen.getByText('Player 2').closest('.player') as HTMLElement
  expect(within(p1).getByText('0/5 skips, 2/3 rerolls')).toHaveClass('streak')
  expect(within(p2).getByText('0/5 skips, 0/2 rerolls')).toHaveClass('streak')
})

test('the skip streak has no reroll count when the house rule is off', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getAllByText('0/5 skips')).toHaveLength(2)
})

test('the key hint names the reroll key, comma-joined, while placing, and is blank while skipping', () => {
  renderScreen(rerollState(true))
  expect(screen.getByText('Arrows move, N next legal spot, Enter places, R rotates, E rerolls')).toBeInTheDocument()

  cleanup()
  renderScreen(rerollState(true, 'skipped'))
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test('the key hint omits the reroll key once charges are exhausted', () => {
  renderScreen(rerollState(false))

  expect(screen.getByText('Arrows move, N next legal spot, Enter places, R rotates')).toBeInTheDocument()
})

test('the turn status line offers reroll as an alternative to a forced skip', () => {
  renderScreen(rerollState(true, 'skipped'))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move — skip (S), or reroll (E)')
})

test('the turn status line skips the reroll mention once charges are exhausted', () => {
  renderScreen(rerollState(false, 'skipped'))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skip (S)')
})

function comebackStates() {
  const turn = { currentPlayerId: 1, turnState: 'choosingPlacement' as const, lastRoll: [3, 4] as [number, number], legalPlacements: [] }
  const before = makeState({ turn })
  const after = makeState({ turn })
  after.game.players['2'].houseRules.comebackNudge.granted = true
  return { before, after }
}

function renderPlaying(state: GameState) {
  const props = { error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const view = render(<PlayingScreen state={state} {...props} />)
  return (next: GameState) => view.rerender(<PlayingScreen state={next} {...props} />)
}

test('a Comeback grant shows a one-time notice naming the player', () => {
  const { before, after } = comebackStates()
  const update = renderPlaying(before)
  expect(screen.queryByText(/Comeback!/)).not.toBeInTheDocument()

  update(after)

  expect(screen.getByText('Comeback! Player 2 gets +1 reroll')).toBeInTheDocument()
})

test('the Comeback notice stays for 8 seconds, longer than an error toast, then disappears', () => {
  vi.useFakeTimers()
  onTestFinished(() => { vi.useRealTimers() })
  const { before, after } = comebackStates()
  const update = renderPlaying(before)

  update(after)
  act(() => vi.advanceTimersByTime(7999))
  expect(screen.getByText(/Comeback!/)).toBeInTheDocument()

  act(() => vi.advanceTimersByTime(1))
  expect(screen.queryByText(/Comeback!/)).not.toBeInTheDocument()
})

test('a flag that was already granted on mount, or stays granted, shows no notice', () => {
  vi.useFakeTimers()
  onTestFinished(() => { vi.useRealTimers() })
  const { after } = comebackStates()
  const update = renderPlaying(after)
  expect(screen.queryByText(/Comeback!/)).not.toBeInTheDocument()

  const { after: later } = comebackStates()
  update(later)
  act(() => vi.advanceTimersByTime(5000))
  expect(screen.queryByText(/Comeback!/)).not.toBeInTheDocument()
})

test('the Comeback notice sits alongside an error toast rather than replacing it', () => {
  const { before, after } = comebackStates()
  const props = { sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const error: GameError = { reason: 'illegalPlacement', message: 'nope' }
  const view = render(<PlayingScreen state={before} error={error} {...props} />)

  view.rerender(<PlayingScreen state={after} error={error} {...props} />)

  expect(screen.getByText('That piece can’t go there — try another spot.')).toBeInTheDocument()
  expect(screen.getByText('Comeback! Player 2 gets +1 reroll')).toBeInTheDocument()
})

test('a Comeback charge makes Reroll usable even when the Reroll rule itself is off', () => {
  const state = rerollState(true)
  state.game.houseRules.reroll = { enabled: false, canReroll: true }
  const sendAction = renderScreen(state)

  fireEvent.click(screen.getByRole('button', { name: 'Reroll' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test('player names in the status line and the Comeback notice never wrap mid-name', () => {
  const { before, after } = comebackStates()
  const update = renderPlaying(before)
  update(after)

  expect(screen.getByTestId('turn-status').textContent).toContain('Player 1')
  expect(screen.getByText(/Comeback!/).textContent).toContain('Player 2')
})

test.each(['ctrlKey', 'metaKey', 'altKey'] as const)('a shortcut key held with %s is left to the browser', (modifier) => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd', [modifier]: true })

  expect(sendAction).not.toHaveBeenCalled()
})

test('shortcuts still work with Caps Lock or Shift held', () => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'D' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'roll' })
})

test('every modal dialog is border-box, so its declared width includes the padding', () => {
  injectPlayingCss()
  const dialog = document.createElement('dialog')
  dialog.className = 'modal'
  document.body.append(dialog)
  onTestFinished(() => dialog.remove())

  expect(getComputedStyle(dialog).boxSizing).toBe('border-box')
})

type GameOver = GameState['game']['gameOver']

function resultBar(gameOver: GameOver, tweak: (game: GameState['game']) => void = () => {}) {
  const game = makeGame({ turn: gameOverTurn, gameOver })
  tweak(game)
  renderScreen({ game, series: null })
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))
  return screen.getByRole('region', { name: 'Game result' })
}

test('the result bar names who surrendered', () => {
  const bar = resultBar({ reason: 'surrender', playerId: 2, winner: 1 })
  expect(within(bar).getByText('Player 2 surrendered')).toBeInTheDocument()
})

test('the result bar states no reason when the board simply settled', () => {
  const bar = resultBar({ reason: 'boardFull', playerId: null, winner: 1 })
  expect(within(bar).queryByText(/board settled/)).not.toBeInTheDocument()
})

test.each([
  ['playerBlocked', 1, 'Player 1 boxed in'],
  ['skipLimit', 2, 'Player 2 hit the skip limit (5 of 5)'],
] as const)('the result bar names the player for a %s ending', (reason, playerId, text) => {
  const bar = resultBar({ reason, playerId, winner: 3 - playerId })
  expect(within(bar).getByText(text)).toBeInTheDocument()
})

test('the end reason sits under the outcome, in the same block', () => {
  const bar = resultBar({ reason: 'playerBlocked', playerId: 1, winner: 2 })
  const reason = within(bar).getByText('Player 1 boxed in')
  expect(reason.previousElementSibling).toHaveTextContent('Player 2 wins on score')
})

test('a tie ended by the skip limit still names the reason on the bar', () => {
  const bar = resultBar({ reason: 'skipLimit', playerId: 1, winner: null })
  expect(within(bar).getByText('Tied')).toBeInTheDocument()
  expect(within(bar).getByText('Player 1 hit the skip limit (5 of 5)')).toBeInTheDocument()
})

test('a win puts the winner’s colour dot beside the outcome on the bar', () => {
  const bar = resultBar({ reason: 'boardFull', playerId: null, winner: 2 })
  expect(bar.querySelector('.dot.p2')).not.toBeNull()
  expect(bar.querySelector('.dot.p1')).toBeNull()
})

test('a tie puts a half-and-half marker, in both colours, in place of the winner dot, beside equal scores', () => {
  const bar = resultBar({ reason: 'boardFull', playerId: null, winner: null }, (game) => {
    game.players['1'].score = { ...game.players['1'].score, totalScore: 150 }
    game.players['2'].score = { ...game.players['2'].score, totalScore: 150 }
  })
  expect(bar.querySelector('.dot.tie')).not.toBeNull()
  expect(bar.querySelector('.dot.p1, .dot.p2')).toBeNull()
  expect(bar).toHaveTextContent('150 – 150')
})

test('mid-game, the header marks the player whose turn it is', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))
  expect(document.querySelector('[aria-current]')).toHaveTextContent('Player 2')
})

test('once the game is over, the header marks no current player', () => {
  renderScreen(gameOverState())
  expect(document.querySelector('[aria-current]')).toBeNull()
  expect(document.querySelector('.header .current')).toBeNull()
})

test('in board view the result bar replaces the player header', () => {
  const bar = resultBar({ reason: 'boardFull', playerId: null, winner: 1 })
  expect(bar).toBeInTheDocument()
  expect(screen.queryByText(/skips/)).not.toBeInTheDocument()
})

test('with the result dialog open, the header still shows both players', () => {
  renderScreen(gameOverState())
  expect(screen.getAllByText(/skips/)).toHaveLength(2)
})

test('the header and the dialog come back with View Result, and View Board swaps them for the bar again', () => {
  renderScreen(gameOverState())
  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))
  expect(screen.queryByText(/skips/)).not.toBeInTheDocument()

  fireEvent.click(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'View Result' }))
  expect(screen.getAllByText(/skips/)).toHaveLength(2)
  expect(screen.getByRole('dialog')).toBeInTheDocument()

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'View Board' }))
  expect(screen.queryByText(/skips/)).not.toBeInTheDocument()
})

test('the bar shows the real score, Player 1 first, even when the winner trails after a surrender', () => {
  const bar = resultBar({ reason: 'surrender', playerId: 2, winner: 1 }, (game) => {
    game.players['1'].score = { ...game.players['1'].score, totalScore: 120 }
    game.players['2'].score = { ...game.players['2'].score, totalScore: 158 }
  })
  expect(bar).toHaveTextContent('120 – 158')
  expect(within(bar).getByText('Player 1 120, Player 2 158')).toBeInTheDocument()
  expect(bar).not.toHaveTextContent(/by \d+ point/)
})

test('focus lands on View Result in the bar after View Board', () => {
  const bar = resultBar({ reason: 'boardFull', playerId: null, winner: 1 })
  expect(within(bar).getByRole('button', { name: 'View Result' })).toHaveFocus()
})

test('focus lands on View Result in the bar after Escape', () => {
  renderScreen(gameOverState())
  fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
  expect(within(screen.getByRole('region', { name: 'Game result' })).getByRole('button', { name: 'View Result' })).toHaveFocus()
})

test('the bar shows total score, not territory, when modifiers make them differ', () => {
  const bar = resultBar({ reason: 'boardFull', playerId: null, winner: 1 }, (game) => {
    game.players['1'].score = { ...game.players['1'].score, totalArea: 152, totalScore: 162 }
    game.players['2'].score = { ...game.players['2'].score, totalArea: 141, totalScore: 141 }
  })
  expect(bar).toHaveTextContent('162 – 141')
})
