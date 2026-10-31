import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, onTestFinished, test, vi } from 'vitest'
import type { ErrorReason } from '../game/gameTypes'
import type { GameError } from '../hooks/useGameSocket'
import { PlayingScreen } from './PlayingScreen'
import { gameOverState, injectPlayingCss, makeState, movesState, recentTurn, renderPlaying, renderScreen, rerollState } from '../dev/testUtils/playingScreenHarness'

afterEach(() => vi.useRealTimers())

test('renders nothing game-specific before the first state broadcast arrives', () => {
  renderScreen(null)
  expect(screen.getByRole('button', { name: 'Menu' })).toBeInTheDocument()
  expect(screen.queryByRole('group', { name: / board$/ })).not.toBeInTheDocument()
})

test('the screen is a main landmark and the rail a named complementary one', () => {
  renderScreen(makeState())

  const main = screen.getByRole('main')
  expect(within(main).getByRole('complementary', { name: 'Scores and moves' })).toBeInTheDocument()
  expect(within(main).getByRole('heading', { level: 1, name: 'Playing' })).toBeInTheDocument()
})

test('the error toast auto-dismisses after 4 seconds', () => {
  vi.useFakeTimers()
  renderScreen(makeState(), vi.fn(), { reason: 'illegalPlacement', message: 'x' })

  act(() => vi.advanceTimersByTime(3999))
  expect(screen.getByRole('status')).not.toBeEmptyDOMElement()

  act(() => vi.advanceTimersByTime(1))
  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

test('a reason this client does not know still shows the generic toast text', () => {
  renderScreen(makeState(), vi.fn(), { reason: 'futureReason' as ErrorReason, message: 'x' })

  expect(screen.getByRole('status')).toHaveTextContent('Something went wrong — try again.')
})

test('the out-of-date toast stays until the page is reloaded', () => {
  vi.useFakeTimers()
  renderScreen(makeState(), vi.fn(), { reason: 'protocolVersionMismatch', message: 'x' })

  act(() => vi.advanceTimersByTime(60_000))

  expect(screen.getByRole('status')).toHaveTextContent('This game is out of date — reload the page.')
})

test('a later error does not replace the out-of-date toast', () => {
  vi.useFakeTimers()
  const props = { state: makeState(), sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const { rerender } = render(<PlayingScreen {...props} error={{ reason: 'protocolVersionMismatch', message: 'x' }} />)

  rerender(<PlayingScreen {...props} error={{ reason: 'illegalPlacement', message: 'y' }} />)
  act(() => vi.advanceTimersByTime(60_000))

  expect(screen.getByRole('status')).toHaveTextContent('This game is out of date — reload the page.')
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

test('the error status region is mounted from the start and empty until an error arrives', () => {
  renderScreen(makeState())

  expect(screen.getByRole('status')).toBeEmptyDOMElement()
})

test('the Playing screen has a level-1 heading', () => {
  renderScreen(makeState())

  expect(screen.getByRole('heading', { level: 1, name: 'Playing' })).toBeInTheDocument()
})

test('Menu carries an M key chip', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByRole('button', { name: 'Menu' }).querySelector('kbd.key-badge')?.textContent).toBe('M')
})

test('the Menu button exposes its keyboard shortcut to assistive tech', () => {
  renderScreen(makeState())

  expect(screen.getByRole('button', { name: 'Menu' })).toHaveAttribute('aria-keyshortcuts', 'm')
})

test('the error toast shows in the rail\'s notice row, a polite status region', () => {
  renderScreen(makeState(), vi.fn(), { reason: 'illegalPlacement', message: 'x' })

  expect(screen.getByRole('status')).toContainElement(screen.getByText(/can’t go there/))
})

function comebackStates() {
  const turn = { currentPlayerId: 1, turnState: 'choosingPlacement' as const, lastRoll: [3, 4] as [number, number], legalPlacements: [], recentTurns: [] }
  const before = makeState({ turn })
  const after = makeState({ turn })
  after.game.players['2'].houseRules.comebackNudge.granted = true
  return { before, after }
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

test('the notice row holds one notice at a time: an error toast first, the Comeback notice waits for it', () => {
  const { before, after } = comebackStates()
  const props = { sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const error: GameError = { reason: 'illegalPlacement', message: 'nope' }
  const view = render(<PlayingScreen state={before} error={error} {...props} />)

  view.rerender(<PlayingScreen state={after} error={error} {...props} />)

  expect(screen.getByText('That piece can’t go there — try another spot.')).toBeInTheDocument()
  expect(screen.queryByText(/Comeback!/)).not.toBeInTheDocument()
})

test('the waiting Comeback notice appears once the error clears, then stays its full 8 seconds', () => {
  vi.useFakeTimers()
  onTestFinished(() => { vi.useRealTimers() })
  const { before, after } = comebackStates()
  const props = { sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn() }
  const error: GameError = { reason: 'illegalPlacement', message: 'nope' }
  const view = render(<PlayingScreen state={before} error={error} {...props} />)
  view.rerender(<PlayingScreen state={after} error={error} {...props} />)

  act(() => vi.advanceTimersByTime(4000))
  expect(screen.queryByText('That piece can’t go there — try another spot.')).not.toBeInTheDocument()
  expect(screen.getByText(/Comeback!/)).toBeInTheDocument()

  act(() => vi.advanceTimersByTime(7999))
  expect(screen.getByText(/Comeback!/)).toBeInTheDocument()
  act(() => vi.advanceTimersByTime(1))
  expect(screen.queryByText(/Comeback!/)).not.toBeInTheDocument()
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
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd', [modifier]: true })

  expect(sendAction).not.toHaveBeenCalled()
})

test('shortcuts still work with Caps Lock or Shift held', () => {
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

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

test('the focus order is the board, then Menu, then the action buttons', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  const board = screen.getByRole('group', { name: / board$/ })
  const menu = screen.getByRole('button', { name: 'Menu' })
  const rotate = screen.getByRole('button', { name: 'Rotate' })
  const follows = (a: Element, b: Element) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)
  expect(follows(board, menu)).toBe(true)
  expect(follows(menu, rotate)).toBe(true)
})

function leavePrevented() {
  const event = new Event('beforeunload', { cancelable: true })
  window.dispatchEvent(event)
  return event.defaultPrevented
}

test('closing or refreshing the tab mid-game asks the browser to confirm once a move has been played', () => {
  renderScreen(movesState([recentTurn(1, 1, [2, 2], 4)]))

  expect(leavePrevented()).toBe(true)
})

test('nothing asks before the first move', () => {
  renderScreen(movesState([]))

  expect(leavePrevented()).toBe(false)
})

test('nothing asks once the game is over', () => {
  renderScreen(gameOverState())

  expect(leavePrevented()).toBe(false)
})

test('leaving the Playing screen removes the leave confirmation', () => {
  renderScreen(movesState([recentTurn(1, 1, [2, 2], 4)]))
  cleanup()

  expect(leavePrevented()).toBe(false)
})
