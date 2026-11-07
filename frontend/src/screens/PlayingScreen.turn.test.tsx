import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { makeGame } from '../dev/fixtures/gameFixtures'
import type { GameWireState } from '../game/gameTypes'
import type { GameState } from '../hooks/useGameSocket'
import { PlayingScreen } from './PlayingScreen'
import { deadRoll, gameOverState, injectPlayingCss, keyboardState, makeState, renderRerenderable, renderScreen, renderVsBot } from '../dev/testUtils/playingScreenHarness'

afterEach(() => vi.useRealTimers())

test('shows a Roll button while awaiting a roll, which sends the roll action', () => {
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.click(screen.getByRole('button', { name: 'Roll' }))
  expect(sendAction).toHaveBeenCalledWith({ type: 'roll' })
})

test('pressing d rolls while awaiting a roll', () => {
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'roll' })
})

test('pressing d does nothing once a roll is already showing', () => {
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [2, 5], legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })
  expect(sendAction).not.toHaveBeenCalled()
})

test('shows the last roll as dice once past awaitingRoll, with Roll hidden', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [2, 5], legalPlacements: [] } }))

  const dice = screen.getByText('2').closest('.dice')
  expect(dice).toContainElement(screen.getByText('5'))
  expect(screen.queryByRole('button', { name: 'Roll' })).not.toBeInTheDocument()
})

test('shows no dice while awaiting a roll', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.queryByRole('img', { name: /rolled/i })).not.toBeInTheDocument()
})

test('shows a Skip button when the turn was skipped, which sends the skip action', () => {
  const sendAction = renderScreen(
    makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }),
  )

  fireEvent.click(screen.getByRole('button', { name: 'Skip' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test('the dice have an accessible name describing the roll', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 1], legalPlacements: [] } }))

  expect(screen.getByRole('img', { name: 'Player 1 rolled 3 and 1' })).toBeInTheDocument()
})

test('the d hotkey does not roll while a modal dialog is open', () => {
  const sendAction = renderScreen(
    makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }),
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

test("on the bot's turn the Roll button is hidden and d does not roll", () => {
  const sendAction = renderVsBot(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 'd' })

  expect(screen.queryByRole('button', { name: 'Roll' })).not.toBeInTheDocument()
  expect(sendAction).not.toHaveBeenCalled()
})

test("on the bot's turn the Skip button is hidden", () => {
  renderVsBot(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))
  expect(screen.queryByRole('button', { name: 'Skip' })).not.toBeInTheDocument()
})

test('the turn status line is a polite live region that is re-read whole', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  const status = screen.getByTestId('turn-status')
  expect(status).toHaveAttribute('aria-live', 'polite')
  expect(status).toHaveAttribute('aria-atomic', 'true')
})

test.each(['awaitingRoll', 'choosingPlacement', 'skipped', 'gameOver'] as const)(
  'Menu sits in the rail head beside the title while %s',
  (turnState) => {
    renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } }))

    const head = screen.getByRole('heading', { name: 'Game' }).parentElement as HTMLElement
    expect(within(head).getByRole('button', { name: 'Menu' })).toBeInTheDocument()
  },
)

test('the turn status line tells the current player what to do: roll', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 2: roll (D)')
})

test('the turn status line names the rectangle to place, following Rotate', () => {
  renderScreen(
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

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 2 wide × 1 tall')
  fireEvent.click(screen.getByRole('button', { name: 'Rotate' }))
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: place 1 wide × 2 tall')
})

test('a dead roll names which skip this would be, against the limit', () => {
  renderScreen({ game: deadRoll(1), series: null })

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skipping… (S) · skip 2 of 5')
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

test('a skip that ends the game is asked for, not announced as happening by itself', () => {
  renderScreen({ game: deadRoll(4), series: null })

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move — skip (S) · skip 5 of 5 ends the game')
})

test('the turn status line says when a dead roll must be skipped', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skipping… (S)')
})

test("the turn status line shows the bot is playing on the bot's turn", () => {
  renderScreen(
    botGame({ current: 2, turnState: 'awaitingRoll' }),
    vi.fn(),
    null,
    vi.fn(),
    2,
  )

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Bot (Greedy) is playing…')
})

interface BotTurn {
  current: 1 | 2
  turnState: GameWireState['turn']['turnState']
  lastRoll?: [number, number] | null
}

function botGame({ current, turnState, lastRoll = null }: BotTurn): GameState {
  const base = makeGame().players
  const wildcard = { enabled: true, originalRoll: null, legalValues: [], editableIndex: null }
  return makeState({
    turn: { recentTurns: [], currentPlayerId: current, turnState, lastRoll, legalPlacements: [] },
    players: { ...base, '2': { ...base['2'], name: 'Bot (Greedy)' } },
    houseRules: { ...makeGame().houseRules, wildcard },
  })
}

// Feeds the screen one state per bot step, the way the socket's paced queue does.
function renderBotGame(first: GameState) {
  const props = { error: null, sendAction: vi.fn(), onOpenSettings: vi.fn(), onNewGame: vi.fn(), botSeat: 2 }
  const view = render(<PlayingScreen state={first} {...props} />)
  return (next: GameState) => view.rerender(<PlayingScreen state={next} {...props} />)
}

test("the bot's last roll is labelled with the bot's name for assistive tech", () => {
  const update = renderBotGame(botGame({ current: 2, turnState: 'choosingPlacement', lastRoll: [3, 5] }))
  expect(screen.getByRole('img', { name: 'Bot (Greedy) rolled 3 and 5' })).toBeInTheDocument()

  update(botGame({ current: 1, turnState: 'awaitingRoll' }))

  expect(screen.getByRole('img', { name: 'Bot (Greedy)’s last roll 3 and 5' })).toHaveTextContent(/^35$/)
})

const rolledState = (turnState: 'choosingPlacement' | 'awaitingRoll', lastRoll: [number, number] | null) =>
  makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll, legalPlacements: [] } })

test('keeps the last roll on screen, marked as the last roll, once the next turn awaits a roll', () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  expect(screen.getByRole('img', { name: 'Player 1 rolled 3 and 5' })).toBeInTheDocument()

  update(rolledState('awaitingRoll', null))

  const dice = screen.getByRole('img', { name: 'Player 1’s last roll 3 and 5' })
  expect(dice).toHaveClass('stale')
  expect(dice).not.toHaveTextContent('last')
  expect(dice.querySelector('.dot')).not.toBeInTheDocument()
})

test('the dice are border-box, so their 34px matches the buttons and the toolbar does not grow on the first roll', () => {
  injectPlayingCss()

  renderScreen(rolledState('choosingPlacement', [3, 5]))

  expect([...document.querySelectorAll('.die')].map((d) => getComputedStyle(d).boxSizing)).toEqual(['border-box', 'border-box'])
})

test('the last roll is marked by a dashed border alone, not by dimming its digits', () => {
  injectPlayingCss()
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  const dice = () => [...document.querySelectorAll('.die')].map((d) => getComputedStyle(d))

  expect(dice().map((c) => c.borderTopStyle)).not.toContain('dashed')

  update(rolledState('awaitingRoll', null))

  expect(dice().map((c) => c.borderTopStyle)).toEqual(['dashed', 'dashed'])
  expect(dice().map((c) => c.opacity)).toEqual(['1', '1'])
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

test('once the game is over no dice show in the rail, not even the last roll dimmed', () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  expect(screen.getByRole('img', { name: 'Player 1 rolled 3 and 5' })).toBeInTheDocument()

  update(gameOverState())

  expect(screen.queryByRole('img', { name: /roll/i })).not.toBeInTheDocument()
  expect(document.querySelector('.rail-dice')).toBeInTheDocument() // the slot stays, so nothing below it moves
})

test('the next round does not open on the previous round\'s last roll', () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))
  update(gameOverState())

  update(rolledState('awaitingRoll', null))

  expect(screen.queryByRole('img', { name: /roll/i })).not.toBeInTheDocument()
})

test('pressing s skips a dead roll', () => {
  const sendAction = renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'skipped', lastRoll: [3, 4], legalPlacements: [] } }))

  fireEvent.keyDown(window, { key: 's' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test('a dead roll with no reroll left skips by itself after a pause', () => {
  vi.useFakeTimers()
  const sendAction = renderScreen({ game: deadRoll(1), series: null })

  act(() => vi.advanceTimersByTime(1499))
  expect(sendAction).not.toHaveBeenCalled()
  act(() => vi.advanceTimersByTime(1))
  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test('a dead roll is not skipped while the screen is paused, and the pause starts again when it clears', () => {
  vi.useFakeTimers()
  const sendAction = vi.fn()
  const screenWith = (paused: boolean) => (
    <PlayingScreen state={{ game: deadRoll(1), series: null }} error={null} sendAction={sendAction} onOpenSettings={vi.fn()} onNewGame={vi.fn()} paused={paused} />
  )
  const view = render(screenWith(true))

  act(() => vi.advanceTimersByTime(10_000))
  expect(sendAction).not.toHaveBeenCalled()
  view.rerender(screenWith(false))
  act(() => vi.advanceTimersByTime(1499))
  expect(sendAction).not.toHaveBeenCalled()
  act(() => vi.advanceTimersByTime(1))
  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test('a dead roll whose skip would end the game waits for S or a click', () => {
  vi.useFakeTimers()
  const sendAction = renderScreen({ game: deadRoll(4), series: null })

  act(() => vi.advanceTimersByTime(10_000))
  expect(sendAction).not.toHaveBeenCalled()
  fireEvent.keyDown(window, { key: 's' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'skip' })
})

test('a dead roll with a reroll usable is left for the player to decide', () => {
  vi.useFakeTimers()
  const game = deadRoll(1)
  game.houseRules.reroll = { enabled: true, canReroll: true }
  const sendAction = renderScreen({ game, series: null })

  act(() => vi.advanceTimersByTime(10_000))
  expect(sendAction).not.toHaveBeenCalled()
})

test("a bot's dead roll is not skipped by the screen", () => {
  vi.useFakeTimers()
  const sendAction = renderScreen({ game: deadRoll(1), series: null }, vi.fn(), null, vi.fn(), 1)

  act(() => vi.advanceTimersByTime(10_000))
  expect(sendAction).not.toHaveBeenCalled()
})

test('a dead roll that moves on within the pause is not skipped', () => {
  vi.useFakeTimers()
  const sendAction = vi.fn()
  const view = render(
    <PlayingScreen state={{ game: deadRoll(1), series: null }} error={null} sendAction={sendAction} onOpenSettings={vi.fn()} onNewGame={vi.fn()} />,
  )

  act(() => vi.advanceTimersByTime(1000))
  view.rerender(
    <PlayingScreen
      state={makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } })}
      error={null}
      sendAction={sendAction}
      onOpenSettings={vi.fn()}
      onNewGame={vi.fn()}
    />,
  )
  act(() => vi.advanceTimersByTime(10_000))
  expect(sendAction).not.toHaveBeenCalled()
})

test('pressing s does nothing when the roll is playable', () => {
  const sendAction = renderScreen(keyboardState())

  fireEvent.keyDown(window, { key: 's' })

  expect(sendAction).not.toHaveBeenCalled()
})

test.each(['awaitingRoll', 'choosingPlacement', 'skipped'] as const)('pressing m opens the Menu in turn state %s', (turnState) => {
  const onOpenSettings = vi.fn()
  const state = makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState, lastRoll: [3, 4], legalPlacements: [] } })
  render(<PlayingScreen state={state} error={null} sendAction={vi.fn()} onOpenSettings={onOpenSettings} onNewGame={vi.fn()} />)

  fireEvent.keyDown(window, { key: 'm' })

  expect(onOpenSettings).toHaveBeenCalledTimes(1)
})

test('Roll sits in the action row, which is where its heavier border is scoped', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByRole('button', { name: 'Roll' }).parentElement).toHaveClass('rail-actions')
})

test('the dice name who rolled them for assistive tech but draw no dot or label', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'choosingPlacement', lastRoll: [4, 2], legalPlacements: [] } }))

  const dice = screen.getByRole('img', { name: 'Player 2 rolled 4 and 2' })
  expect(dice.querySelector('.dot')).not.toBeInTheDocument()
  expect(dice).toHaveTextContent(/^42$/)
})

test("a dimmed last roll keeps its roller's name for assistive tech through the next player's turn", () => {
  const update = renderRerenderable(rolledState('choosingPlacement', [3, 5]))

  update(makeState({ turn: { recentTurns: [], currentPlayerId: 2, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))

  expect(screen.getByRole('img', { name: 'Player 1’s last roll 3 and 5' })).toHaveTextContent(/^35$/)
})

test('the dice slot is always in the rail, and reserves the Wildcard picker height only while that rule is on', () => {
  const off = makeState()
  off.game.houseRules.wildcard = { ...off.game.houseRules.wildcard, enabled: false }
  renderScreen(off)
  expect(document.querySelector('.rail-dice')).not.toBeNull()
  expect(document.querySelector('.rail-dice')).not.toHaveClass('reserves-picker')

  cleanup()
  const on = makeState()
  on.game.houseRules.wildcard = { ...on.game.houseRules.wildcard, enabled: true }
  renderScreen(on)
  expect(document.querySelector('.rail-dice')).toHaveClass('reserves-picker')
})

test('the status line and key hint sit together in one reserved box, with the dice slot and action row after it', () => {
  renderScreen(makeState())

  const box = document.querySelector('.rail-instr') as HTMLElement
  expect(box).toContainElement(document.getElementById('board-help'))
  expect(box.nextElementSibling).toHaveClass('rail-dice')
  expect(document.querySelector('.rail-actions')).toBe(box.nextElementSibling!.nextElementSibling)
})

test('a roll is announced in a polite live region, with the roller\'s name', () => {
  renderScreen(keyboardState())
  const announcement = screen.getByTestId('roll-announcement')
  expect(announcement).toHaveAttribute('aria-live', 'polite')
  expect(announcement).toHaveTextContent('Player 1 rolled 2 and 1')
})

test('a Wildcard roll is announced too, although its dice are replaced by the picker', () => {
  renderScreen(
    makeState({
      turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingWildcard', lastRoll: [6, 6], legalPlacements: [] },
      houseRules: { ...makeGame().houseRules, wildcard: { enabled: true, originalRoll: [6, 6], legalValues: [1, 2, 3], editableIndex: 0 } },
    }),
  )
  expect(screen.getByTestId('roll-announcement')).toHaveTextContent('Player 1 rolled 6 and 6')
})

test('nothing is announced while there is no roll', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'awaitingRoll', lastRoll: null, legalPlacements: [] } }))
  expect(screen.getByTestId('roll-announcement')).toBeEmptyDOMElement()
})
