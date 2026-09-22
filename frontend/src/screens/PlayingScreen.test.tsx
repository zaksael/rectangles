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
