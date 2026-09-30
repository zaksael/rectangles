import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { makeGame } from '../testUtils/gameFixtures'
import { GameOverOverlay } from './GameOverOverlay'

afterEach(cleanup)

interface Result {
  winner: 1 | 2 | null
  reason?: 'boardFull' | 'playerBlocked' | 'skipLimit' | 'surrender'
  playerId?: number | null
  area: [number, number]
  score?: [number, number]
}

function renderOver({ winner, reason = 'boardFull', playerId = null, area, score = area }: Result, tweak: (game: ReturnType<typeof makeGame>) => void = () => {}) {
  const game = makeGame({ gameOver: { reason, playerId, winner } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: area[0], totalScore: score[0] }
  game.players['2'].score = { ...game.players['2'].score, totalArea: area[1], totalScore: score[1] }
  tweak(game)
  render(<GameOverOverlay game={game} onNewGame={vi.fn()} />)
  return screen.getByRole('dialog')
}

test('a win on score states the margin in points', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(dialog).toHaveAccessibleDescription('by 17 points')
})

test('a surrender states no margin, since the winner can trail on score', () => {
  const dialog = renderOver({ winner: 2, reason: 'surrender', playerId: 1, area: [158, 141] })
  expect(dialog).not.toHaveAccessibleDescription()
})

test('a tie states no margin', () => {
  const dialog = renderOver({ winner: null, area: [150, 150] })
  expect(dialog).not.toHaveAccessibleDescription()
})

function withRules(game: ReturnType<typeof makeGame>) {
  game.houseRules.prize = { enabled: true, cells: [], points: 10 }
  game.houseRules.steal = { enabled: true, cells: [], points: 10 }
  game.houseRules.selfEnclosedPenalty = { enabled: true }
}

test('the modifier with the biggest swing is named in the story and tagged in the table', () => {
  const dialog = renderOver({ winner: 1, area: [152, 141], score: [162, 148] }, (game) => {
    withRules(game)
    game.players['1'].houseRules.prize.captured = 1 // swing 10 (prize 1 vs 0)
    game.players['1'].houseRules.steal.captured = 1 // swing 20 (+10 vs -10)
  })
  expect(dialog).toHaveAccessibleDescription('by 14 points. Biggest swing: Steal, 20.')
  expect(within(dialog).getByRole('row', { name: /Steal/ })).toHaveTextContent('Biggest swing')
  expect(within(dialog).getByRole('row', { name: /Prize/ })).not.toHaveTextContent('Biggest swing')
})

test('a swing under half the margin is neither tagged nor named', () => {
  const dialog = renderOver({ winner: 1, area: [200, 150], score: [200, 147] }, (game) => {
    withRules(game)
    game.players['2'].houseRules.selfEnclosedPenalty.cells = 3 // swing 3 of a 53-point margin
  })
  expect(dialog).toHaveAccessibleDescription('by 53 points')
  expect(dialog).not.toHaveTextContent('Biggest swing')
})

test('a winner who trailed on territory names the modifiers that turned it, instead of the swing', () => {
  const dialog = renderOver({ winner: 2, area: [150, 144], score: [140, 154] }, (game) => {
    game.houseRules.prize = { enabled: true, cells: [], points: 10 }
    game.houseRules.pitfall = { enabled: true, cells: [], points: 10 }
    game.players['2'].houseRules.prize.captured = 1
    game.players['1'].houseRules.pitfall.captured = 1
  })
  expect(dialog).toHaveAccessibleDescription('by 14 points. Trailed by 6 on territory, won on Prize and Pitfall.')
})

test('each modifier row states its rule with the point value from the game', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141], score: [160, 141] }, (game) => {
    game.houseRules.prize = { enabled: true, cells: [], points: 10 }
    game.houseRules.pitfall = { enabled: true, cells: [], points: 7 }
    game.houseRules.steal = { enabled: true, cells: [], points: 12 }
    game.houseRules.selfEnclosedPenalty = { enabled: true }
    game.players['1'].houseRules.prize.captured = 1
    game.players['1'].houseRules.pitfall.captured = 1
    game.players['1'].houseRules.steal.captured = 1
    game.players['2'].houseRules.selfEnclosedPenalty.cells = 2
  })
  const note = (label: RegExp) => within(dialog).getByRole('row', { name: label }).querySelector('th')?.textContent
  expect(note(/^Prize/)).toContain('+10 per captured cell')
  expect(note(/^Pitfall/)).toContain('−7 per captured cell')
  expect(note(/^Steal/)).toContain('±12 per capture, zero-sum')
  expect(note(/^Enclosure/)).toContain('−1 per sealed-in cell')
})

test('a modifier row where both players are at zero is hidden, but a single zero beside a non-zero stays, muted', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141], score: [168, 141] }, (game) => {
    withRules(game)
    game.players['1'].houseRules.prize.captured = 1 // Prize 10 vs 0 stays; Steal and Enclosure are 0 vs 0
  })
  expect(within(dialog).getByRole('row', { name: /^Prize/ })).toBeInTheDocument()
  expect(within(dialog).queryByRole('row', { name: /^Steal/ })).not.toBeInTheDocument()
  expect(within(dialog).queryByRole('row', { name: /^Enclosure/ })).not.toBeInTheDocument()
  const [own, theirs] = within(dialog).getByRole('row', { name: /^Prize/ }).querySelectorAll('td')
  expect(own).not.toHaveClass('zero')
  expect(theirs).toHaveClass('zero')
})

test('a game with no modifier rows collapses Territory and Final score into one row', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(within(dialog).queryByRole('row', { name: /^Territory/ })).not.toBeInTheDocument()
  const row = within(dialog).getByRole('row', { name: /Final score/ })
  expect(row).toHaveTextContent('Final score (territory)158141')
})

test('with modifier rows, Territory and Final score stay separate', () => {
  const dialog = renderOver({ winner: 1, area: [152, 141], score: [162, 141] }, (game) => {
    withRules(game)
    game.players['1'].houseRules.prize.captured = 1
  })
  expect(within(dialog).getByRole('row', { name: /^Territory/ })).toHaveTextContent('Territory152141')
  expect(within(dialog).getByRole('row', { name: /^Final score/ })).toHaveTextContent('Final score162141')
})

test('a surrender labels the total "Score at surrender"', () => {
  const dialog = renderOver({ winner: 2, reason: 'surrender', playerId: 1, area: [158, 141] })
  expect(within(dialog).getByRole('row', { name: /Score at surrender/ })).toHaveTextContent('Score at surrender158141')
})

test.each([
  [1, '1'],
  [2, '2'],
  [null, 'tie'],
] as const)('the dialog marks its outcome for styling (winner %s)', (winner, outcome) => {
  const dialog = renderOver({ winner, area: [158, 141] })
  expect(dialog).toHaveAttribute('data-outcome', outcome)
})
