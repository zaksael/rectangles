import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
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
  expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument()
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

test('shows the last roll as dice once past awaitingRoll, with no Roll button', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [2, 5], legalPlacements: [] } }))

  const dice = screen.getByText('2').closest('.dice')
  expect(dice).toContainElement(screen.getByText('5'))
  expect(screen.queryByRole('button', { name: 'Roll' })).not.toBeInTheDocument()
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

test.each(['awaitingRoll', 'choosingPlacement'] as const)('has no Skip button while %s', (turnState) => {
  renderScreen(makeState({ turn: { currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.queryByRole('button', { name: 'Skip' })).not.toBeInTheDocument()
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

  expect(screen.getByRole('img', { name: 'Rolled 3 and 1' })).toBeInTheDocument()
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
  expect(within(dialog).getByText('Board settled')).toBeInTheDocument()
  expect(within(dialog).getByRole('heading', { name: 'Player\u00a01 wins' })).toBeInTheDocument()
})

test('no game-over dialog while the game is in progress', () => {
  renderScreen(makeState())
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

test.each([
  ['playerBlocked', 2, 'Player 2 boxed in'],
  ['skipLimit', 1, 'Player 1 skipped out (5 of 5)'],
  ['surrender', 2, 'Player 2 surrendered'],
] as const)('game over names the player for a %s ending', (reason, playerId, text) => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason, playerId, winner: 1 } }))
  expect(within(screen.getByRole('dialog')).getByText(text)).toBeInTheDocument()
})

test('game over reads "Tied" when there is no winner', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: null } }))
  expect(within(screen.getByRole('dialog')).getByRole('heading', { name: 'Tied' })).toBeInTheDocument()
})

test('game over shows a per-player territory and final-score breakdown', () => {
  const game = makeGame({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: 5, totalScore: 5 }
  game.players['2'].score = { ...game.players['2'].score, totalArea: 4, totalScore: 4 }
  renderScreen({ game, series: null })

  const table = within(screen.getByRole('dialog')).getByRole('table')
  const row = (name: string) => within(table).getByRole('row', { name: new RegExp(name) })
  const rowValues = (name: string) => [
    within(row(name)).getByRole('rowheader').textContent,
    ...within(row(name)).getAllByRole('cell').map((c) => c.textContent),
  ]
  expect(rowValues('Territory')).toEqual(['Territory', '5', '4'])
  expect(rowValues('Final score')).toEqual(['Final score', '5', '4'])
  expect(within(table).getAllByRole('columnheader').map((c) => c.textContent)).toEqual(['Score', 'Player\u00a01', 'Player\u00a02'])
  expect(within(table).queryByRole('row', { name: /Prize/ })).not.toBeInTheDocument()
})

test('Surrender opens a confirm dialog naming the opponent as winner, without sending anything', () => {
  const sendAction = renderScreen(makeState({ turn: { currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.click(screen.getByRole('button', { name: 'Surrender' }))

  const dialog = screen.getByRole('dialog')
  expect(within(dialog).getByText('Surrender the match?')).toBeInTheDocument()
  expect(within(dialog).getByText(/Player 2 wins immediately/)).toBeInTheDocument()
  expect(sendAction).not.toHaveBeenCalled()
})

function openSurrender(state = makeState()) {
  const sendAction = renderScreen(state)
  fireEvent.click(screen.getByRole('button', { name: 'Surrender' }))
  return { sendAction, dialog: screen.getByRole('dialog') }
}

test('confirming Surrender sends the action and closes the dialog', () => {
  const { sendAction, dialog } = openSurrender()

  fireEvent.click(within(dialog).getByRole('button', { name: 'Surrender' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'surrender' })
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

test('Cancel closes the Surrender dialog without sending anything', () => {
  const { sendAction, dialog } = openSurrender()

  fireEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))

  expect(sendAction).not.toHaveBeenCalled()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

test('Escape cancels the Surrender dialog', () => {
  const { sendAction, dialog } = openSurrender()

  fireEvent(dialog, new Event('cancel', { cancelable: true }))

  expect(sendAction).not.toHaveBeenCalled()
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
})

test('Surrender copy says the round, not the match, mid-series', () => {
  const { dialog } = openSurrender({ ...makeState(), series: { length: 3 } as GameState['series'] })

  expect(within(dialog).getByText('Surrender this round?')).toBeInTheDocument()
  expect(within(dialog).getByText(/The series continues to the next round/)).toBeInTheDocument()
})

test('the Surrender button is gone once the game is over', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))
  expect(screen.queryByRole('button', { name: 'Surrender' })).not.toBeInTheDocument()
})

test('the game-over dialog offers New Game', () => {
  const onNewGame = vi.fn()
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }), vi.fn(), null, onNewGame)

  fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'New Game' }))

  expect(onNewGame).toHaveBeenCalledTimes(1)
})

test('game-over player names use a non-breaking space so they never wrap mid-name', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))
  expect(within(screen.getByRole('dialog')).getByRole('heading').textContent).toBe('Player\u00a01 wins')
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
  expect(screen.getByRole('button', { name: 'Rotate' })).toBeDisabled()
})

test("on the bot's turn the Roll button is disabled and d does not roll", () => {
  const sendAction = renderVsBot(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })

  expect(screen.getByRole('button', { name: 'Roll' })).toBeDisabled()
  expect(sendAction).not.toHaveBeenCalled()
})

test("on the bot's turn the Skip button is disabled", () => {
  renderVsBot(makeState({ turn: { currentPlayerId: 2, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))
  expect(screen.getByRole('button', { name: 'Skip' })).toBeDisabled()
})

test("on the human's turn against a bot, placement still works", () => {
  const sendAction = renderVsBot(makeState({ board: { size: 5, skipLimit: 5 }, turn: { ...botPlacementTurn, currentPlayerId: 1 } }))

  fireEvent.pointerUp(screen.getByRole('grid').querySelector('[data-cell="0,0"]')!, { pointerType: 'mouse' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'place', topLeft: [0, 0], width: 2, height: 1 })
})

test('announces whose turn it is in a polite live region', () => {
  renderScreen(makeState({ turn: { currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  const announcer = document.querySelector('.turn-announcer')
  expect(announcer).toHaveAttribute('aria-live', 'polite')
  expect(announcer).toHaveTextContent('Player 2’s turn')
})

test('does not announce a turn once the game is over', () => {
  renderScreen(makeState({ turn: gameOverTurn, gameOver: { reason: 'boardFull', playerId: null, winner: 1 } }))
  expect(document.querySelector('.turn-announcer')).not.toBeInTheDocument()
})

test("on the bot's turn Surrender is disabled, since it would make the bot surrender", () => {
  renderVsBot(makeState({ turn: botPlacementTurn }))
  expect(screen.getByRole('button', { name: 'Surrender' })).toBeDisabled()
})

test('there is no Replay button mid-game; Replay is only reachable from the game-over dialog', () => {
  renderScreen(makeState())
  expect(screen.queryByRole('button', { name: 'Replay' })).not.toBeInTheDocument()
})
