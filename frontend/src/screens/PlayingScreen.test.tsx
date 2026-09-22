import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../testUtils/gameFixtures'
import type { GameState } from '../useGameSocket'
import { PlayingScreen } from './PlayingScreen'

function makeState(overrides: Parameters<typeof makeGame>[0] = {}): GameState {
  return { game: makeGame(overrides), series: null }
}

function renderScreen(state: GameState | null, sendAction = vi.fn()) {
  render(
    <PlayingScreen
      state={state}
      error={null}
      sendAction={sendAction}
      onOpenSettings={vi.fn()}
      onGoToReplay={vi.fn()}
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
