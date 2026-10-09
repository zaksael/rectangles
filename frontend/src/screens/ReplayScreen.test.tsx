import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { GameWireState, HistoryEntry } from '../gameTypes'
import { makeGame } from '../fixtures/gameFixtures'
import { ReplayScreen } from './ReplayScreen'

afterEach(cleanup)

const place = (playerId: number, topLeft: [number, number], width: number, height: number): HistoryEntry => ({
  playerId,
  roll: [width, height],
  placed: { topLeft, width, height },
  wildcardOriginalRoll: null,
  score: { '1': 0, '2': 0 },
})

function replayGame(history: HistoryEntry[], tweak: (game: GameWireState) => void = () => {}): GameWireState {
  const game = makeGame({ board: { size: 5, skipLimit: 5 } })
  game.gameOver = { reason: 'boardFull', playerId: null, winner: 1, history }
  tweak(game)
  return game
}

const TWO_MOVES = [place(1, [0, 0], 2, 2), place(2, [3, 3], 2, 2)]

const pieces = (container: HTMLElement) => container.querySelectorAll('.piece-outline')

test('opens on the start of the game: empty board, no way back from step 0', () => {
  const { container } = render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(pieces(container)).toHaveLength(0)
  expect(screen.getByText('Turn 0 of 2')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'First' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Prev' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled()
})

test('Next places the first move, and only that piece carries the last-piece cue', () => {
  const { container } = render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  expect(screen.getByText('Turn 1 of 2')).toBeTruthy()
  expect(pieces(container)).toHaveLength(1)
  expect(container.querySelectorAll('.piece-outline.last')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'First' })).toBeEnabled()
})

test('Last shows every piece and ends the stepping; First and Prev walk back', () => {
  const { container } = render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  expect(screen.getByText('Turn 2 of 2')).toBeTruthy()
  expect(pieces(container)).toHaveLength(2)
  expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Last' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Prev' }))
  expect(screen.getByText('Turn 1 of 2')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'First' }))
  expect(screen.getByText('Turn 0 of 2')).toBeTruthy()
  expect(pieces(container)).toHaveLength(0)
})

test('a skip step leaves the board as it was and marks no piece', () => {
  const skip: HistoryEntry = { playerId: 2, roll: [6, 6], placed: null, wildcardOriginalRoll: null, score: { '1': 0, '2': 0 } }
  const { container } = render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2), skip])} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  expect(screen.getByText('Turn 2 of 2')).toBeTruthy()
  expect(pieces(container)).toHaveLength(1)
  expect(container.querySelectorAll('.piece-outline.last')).toHaveLength(0)
})

test('an all-skips game opens with nothing to step through', () => {
  render(<ReplayScreen game={replayGame([])} onBack={vi.fn()} />)
  expect(screen.getByText('Turn 0 of 0')).toBeTruthy()
  for (const name of ['First', 'Prev', 'Next', 'Last']) expect(screen.getByRole('button', { name })).toBeDisabled()
})

test('hatching follows the step: a pocket the first move seals shows only from then on', () => {
  // Four strips of Player 1 forming a 3x3 ring around the empty cell (1,1).
  const ring = [place(1, [0, 0], 3, 1), place(1, [0, 0], 1, 3), place(1, [2, 0], 3, 1), place(1, [0, 2], 1, 3)]
  const game = replayGame(ring, (g) => {
    g.houseRules.selfEnclosedPenalty = { enabled: true }
  })
  const { container } = render(<ReplayScreen game={game} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  expect(container.querySelectorAll('.enclosed-hatch.p1')).toHaveLength(1)
  fireEvent.click(screen.getByRole('button', { name: 'Prev' }))
  expect(container.querySelectorAll('.enclosed-hatch')).toHaveLength(0)
})

test('Back calls onBack', () => {
  const onBack = vi.fn()
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={onBack} />)
  fireEvent.click(screen.getByRole('button', { name: 'Back' }))
  expect(onBack).toHaveBeenCalledOnce()
})
