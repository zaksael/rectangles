import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { GameWireState, HistoryEntry, ScoreParts } from '../gameTypes'
import { makeGame } from '../fixtures/gameFixtures'
import { ReplayScreen } from './ReplayScreen'

afterEach(cleanup)

const parts = (overrides: Partial<ScoreParts> = {}): ScoreParts => ({ area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0, ...overrides })
const total = (p: ScoreParts) => p.area + p.prize + p.pitfall + p.steal + p.enclosure

// A history entry; `breakdown` gives each player's score parts at that step (score is their sum).
const move = (
  playerId: number,
  placed: HistoryEntry['placed'],
  breakdown: { '1'?: Partial<ScoreParts>; '2'?: Partial<ScoreParts> } = {},
  extra: Partial<HistoryEntry> = {},
): HistoryEntry => {
  const b = { '1': parts(breakdown['1']), '2': parts(breakdown['2']) }
  return { playerId, roll: [2, 2], placed, wildcardOriginalRoll: null, score: { '1': total(b['1']), '2': total(b['2']) }, breakdown: b, ...extra }
}

const place = (playerId: number, topLeft: [number, number], width: number, height: number, breakdown = {}): HistoryEntry =>
  move(playerId, { topLeft, width, height }, breakdown, { roll: [width, height] })

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
  expect(screen.getByText('Start of game')).toBeTruthy()
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
  expect(screen.getByText('Start of game')).toBeTruthy()
  expect(pieces(container)).toHaveLength(0)
})

test('a skip step leaves the board as it was and marks no piece', () => {
  const skip = move(2, null, {}, { roll: [6, 6] })
  const { container } = render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2), skip])} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  expect(screen.getByText('Turn 2 of 2')).toBeTruthy()
  expect(pieces(container)).toHaveLength(1)
  expect(container.querySelectorAll('.piece-outline.last')).toHaveLength(0)
})

test('an all-skips game opens with nothing to step through', () => {
  render(<ReplayScreen game={replayGame([])} onBack={vi.fn()} />)
  expect(screen.getByText('Start of game')).toBeTruthy()
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

const caption = () => screen.getByTestId('replay-caption')
const next = () => fireEvent.click(screen.getByRole('button', { name: 'Next' }))

test('the caption opens on the start of the game', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(caption()).toHaveTextContent('Start of gameNo moves played yet')
})

test('the caption names the turn, the player, the rectangle and where it went', () => {
  render(<ReplayScreen game={replayGame([place(1, [11, 7], 3, 4)])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('Turn 1 of 1Player 1 placed a 3×4 rectangle at (11, 7)')
})

test('a skip step reads skipped with the roll', () => {
  render(<ReplayScreen game={replayGame([move(2, null, {}, { roll: [3, 4] })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('Player 2 skipped (rolled 3, 4)')
})

test('a wildcard placement ends with the roll before the edit', () => {
  render(<ReplayScreen game={replayGame([move(1, { topLeft: [0, 0], width: 2, height: 5 }, {}, { wildcardOriginalRoll: [3, 4] })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('Player 1 placed a 2×5 rectangle at (0, 0) (wildcard: rolled 3, 4)')
})

test('the caption is a polite live region', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(caption()).toHaveAttribute('aria-live', 'polite')
})

test('a Prize capture is named with its points, and not again on a later step that adds nothing', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4, prize: 5 } }), place(1, [3, 3], 1, 1, { '1': { area: 5, prize: 5 } })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('placed a 2×2 rectangle at (0, 0) — captures Prize (+5)')
  next()
  expect(caption()).not.toHaveTextContent('Prize')
})

test('a Pitfall hit is named with its penalty', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4, pitfall: -3 } })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('— hits Pitfall (−3)')
})

test('a Steal names what the opponent loses', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4, steal: 4 }, '2': { steal: -4 } })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('— captures Steal (+4, Player 2 −4)')
})

test('sealing in own cells is named with the cells and the penalty', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 1, 1, { '1': { area: 1 } }), place(1, [2, 2], 1, 1, { '1': { area: 2, enclosure: -2 } })])} onBack={vi.fn()} />)
  next()
  next()
  expect(caption()).toHaveTextContent('— encloses 2 of its own cells (−2)')
})

test('several effects share one dash, in order', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4, prize: 5, pitfall: -3 } })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('(0, 0) — captures Prize (+5), hits Pitfall (−3)')
})

const lastStepCaption = (reason: GameWireState['gameOver']['reason'], playerId: number | null, winner: number | null) => {
  const game = replayGame([place(1, [0, 0], 2, 2), move(2, null)], (g) => {
    g.gameOver = { ...g.gameOver, reason, playerId, winner }
  })
  render(<ReplayScreen game={game} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  return caption()
}

test('the last step names the end reason in the game-over dialog\'s words', () => {
  expect(lastStepCaption('boardFull', null, 1)).toHaveTextContent('Player 2 skipped (rolled 2, 2) — board settled')
  cleanup()
  expect(lastStepCaption('playerBlocked', 2, 1)).toHaveTextContent('— Player 2 had no legal move left')
  cleanup()
  expect(lastStepCaption('skipLimit', 2, 1)).toHaveTextContent('— Player 2 hit the skip limit (5 of 5)')
  cleanup()
  expect(lastStepCaption('surrender', 2, 1)).toHaveTextContent('— Player 2 surrendered, Player 1 wins')
})

test('only the last step carries the end reason', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  next()
  expect(caption()).not.toHaveTextContent('board settled')
})

const cellsOf = (label: string) =>
  within(screen.getByRole('rowheader', { name: label }).closest('tr')!)
    .getAllByRole('cell')
    .map((cell) => cell.textContent)
const rowLabels = () => screen.getAllByRole('rowheader').map((header) => header.textContent)
const rulesOn = (...rules: ('prize' | 'pitfall' | 'steal' | 'selfEnclosedPenalty')[]) => (g: GameWireState) => {
  for (const rule of rules) g.houseRules[rule].enabled = true
}

test('the table starts at zero and follows the step: Area and Total per player', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4 } })])} onBack={vi.fn()} />)
  expect(cellsOf('Total')).toEqual(['0', '0'])
  next()
  expect(cellsOf('Area')).toEqual(['4', '0'])
  expect(cellsOf('Total')).toEqual(['4', '0'])
})

test('a rule gets a row only when it is on', () => {
  const history = [place(1, [0, 0], 2, 2, { '1': { area: 4 } })]
  render(<ReplayScreen game={replayGame(history)} onBack={vi.fn()} />)
  expect(rowLabels()).toEqual(['Area', 'Total'])
  cleanup()
  render(<ReplayScreen game={replayGame(history, rulesOn('prize'))} onBack={vi.fn()} />)
  expect(rowLabels()).toEqual(['Area', 'Prize', 'Total'])
  cleanup()
  render(<ReplayScreen game={replayGame(history, rulesOn('prize', 'pitfall', 'steal', 'selfEnclosedPenalty'))} onBack={vi.fn()} />)
  expect(rowLabels()).toEqual(['Area', 'Prize', 'Pitfall', 'Steal', 'Enclosure', 'Total'])
})

test('rule rows are signed with a real minus sign, and the total can go below zero', () => {
  const game = replayGame([place(1, [0, 0], 1, 1, { '1': { area: 1, prize: 5, pitfall: -8 }, '2': { steal: 3 } })], rulesOn('prize', 'pitfall', 'steal'))
  render(<ReplayScreen game={game} onBack={vi.fn()} />)
  next()
  expect(cellsOf('Prize')).toEqual(['+5', '0'])
  expect(cellsOf('Pitfall')).toEqual(['−8', '0'])
  expect(cellsOf('Steal')).toEqual(['0', '+3'])
  expect(cellsOf('Total')).toEqual(['−2', '3'])
})

test('a zero in a rule row is muted, a real amount is not', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 1, 1, { '1': { area: 1, prize: 5 } })], rulesOn('prize'))} onBack={vi.fn()} />)
  next()
  const [mine, theirs] = within(screen.getByRole('rowheader', { name: 'Prize' }).closest('tr')!).getAllByRole('cell')
  expect(mine).not.toHaveClass('zero')
  expect(theirs).toHaveClass('zero')
})

test('the table is labelled by its step, has scoped headers, and is not a live region', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(screen.getByRole('table', { name: 'Score at the start of the game' })).toBeTruthy()
  next()
  const table = screen.getByRole('table', { name: 'Score at turn 1' })
  expect(within(table).getAllByRole('columnheader').map((h) => h.textContent)).toEqual(['Player 1', 'Player 2'])
  expect(within(table).getAllByRole('columnheader')[0]).toHaveAttribute('scope', 'col')
  expect(within(table).getByRole('rowheader', { name: 'Area' })).toHaveAttribute('scope', 'row')
  expect(table.querySelector('caption')).toHaveClass('visually-hidden')
  expect(table.closest('[aria-live]')).toBeNull()
})

test('the opponent is named in the table header as on Playing', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES, (g) => { g.players['2'].name = 'Bot (hard)' })} onBack={vi.fn()} />)
  expect(screen.getByRole('columnheader', { name: 'Bot (hard)' })).toBeTruthy()
})
