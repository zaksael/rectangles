import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
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

function renderOver(
  { winner, reason = 'boardFull', playerId = null, area, score = area }: Result,
  tweak: (game: ReturnType<typeof makeGame>) => void = () => {},
  handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() },
) {
  const game = makeGame({ gameOver: { reason, playerId, winner } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: area[0], totalScore: score[0] }
  game.players['2'].score = { ...game.players['2'].score, totalArea: area[1], totalScore: score[1] }
  tweak(game)
  render(<GameOverOverlay game={game} {...handlers} />)
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

test('the modifier with the biggest swing is tagged in the table, and not repeated in the story', () => {
  const dialog = renderOver({ winner: 1, area: [152, 141], score: [162, 148] }, (game) => {
    withRules(game)
    game.players['1'].houseRules.prize.captured = 1 // swing 10 (prize 1 vs 0)
    game.players['1'].houseRules.steal.captured = 1 // swing 20 (+10 vs -10)
  })
  expect(dialog).toHaveAccessibleDescription('by 14 points')
  expect(within(dialog).getByRole('row', { name: /Steal/ })).toHaveTextContent('Biggest swing')
  expect(within(dialog).getByRole('row', { name: /Prize/ })).not.toHaveTextContent('Biggest swing')
  // The tag is separated from the label in the row header's accessible name; other rows get no separator.
  expect(within(dialog).getByRole('rowheader', { name: /^Steal, Biggest swing/ })).toBeInTheDocument()
  expect(within(dialog).getByRole('rowheader', { name: /^Prize\+/ })).toBeInTheDocument()
})

test('a swing under half the margin is not tagged', () => {
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

test('with modifier rows, the table keeps a Territory row', () => {
  const dialog = renderOver({ winner: 1, area: [152, 141], score: [162, 141] }, (game) => {
    withRules(game)
    game.players['1'].houseRules.prize.captured = 1
  })
  expect(within(dialog).getByRole('row', { name: /^Territory/ })).toHaveTextContent('Territory152141')
})

test.each([
  [1, '1'],
  [2, '2'],
  [null, 'tie'],
] as const)('the dialog marks its outcome for styling (winner %s)', (winner, outcome) => {
  const dialog = renderOver({ winner, area: [158, 141] })
  expect(dialog).toHaveAttribute('data-outcome', outcome)
})

test('View Board comes first and holds focus; New Game is second', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  const buttons = within(dialog).getAllByRole('button')
  expect(buttons.map((b) => b.textContent)).toEqual(['View Board', 'New Game'])
  expect(buttons[0]).toHaveFocus()
})

test('View Board and New Game call their handlers', () => {
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderOver({ winner: 1, area: [158, 141] }, undefined, handlers)
  fireEvent.click(within(dialog).getByRole('button', { name: 'View Board' }))
  expect(handlers.onViewBoard).toHaveBeenCalledTimes(1)
  fireEvent.click(within(dialog).getByRole('button', { name: 'New Game' }))
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
})

test('Escape shows the board instead of closing the result for good', () => {
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderOver({ winner: 1, area: [158, 141] }, undefined, handlers)
  const cancel = new Event('cancel', { cancelable: true })
  fireEvent(dialog, cancel)
  expect(handlers.onViewBoard).toHaveBeenCalledTimes(1)
  expect(cancel.defaultPrevented).toBe(true)
})

test('a one-point margin reads "1 point"', () => {
  const dialog = renderOver({ winner: 1, area: [142, 141] })
  expect(dialog).toHaveAccessibleDescription('by 1 point')
})

test('the final score is not a row of the table', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(within(dialog).queryByRole('row', { name: /Final score/ })).not.toBeInTheDocument()
})

const scoreCell = (dialog: HTMLElement, total: string) =>
  within(within(dialog).getByRole('group', { name: 'Final score' })).getByText(total).closest('.lead, .trail')

test('the winner’s total is at full ink and the other muted', () => {
  const dialog = renderOver({ winner: 2, area: [141, 158] })
  expect(scoreCell(dialog, '158')).toHaveClass('lead')
  expect(scoreCell(dialog, '141')).toHaveClass('trail')
})

test('a tie leaves both totals at full ink', () => {
  const dialog = renderOver({ winner: null, area: [150, 149], score: [150, 149] })
  expect(scoreCell(dialog, '150')).toHaveClass('lead')
  expect(scoreCell(dialog, '149')).toHaveClass('lead')
})

test('a surrender captions the score and leaves both totals at full ink, even when the winner trails', () => {
  const dialog = renderOver({ winner: 2, reason: 'surrender', playerId: 1, area: [158, 141] })
  expect(within(dialog).getByText('Score at surrender')).toBeInTheDocument()
  expect(scoreCell(dialog, '158')).toHaveClass('lead')
  expect(scoreCell(dialog, '141')).toHaveClass('lead')
})

const winnerCell = (dialog: HTMLElement) =>
  within(within(dialog).getByRole('group', { name: 'Final score' })).getAllByText(/^\d+$/).map((n) => n.closest('.winner'))

test('only the winner’s score cell is marked', () => {
  const dialog = renderOver({ winner: 2, area: [141, 158] })
  const [first, second] = winnerCell(dialog)
  expect(first).toBeNull()
  expect(second).toHaveClass('winner')
})

test('a winner who trails on score is still marked after a surrender', () => {
  const dialog = renderOver({ winner: 2, reason: 'surrender', playerId: 1, area: [158, 141] })
  expect(winnerCell(dialog)[1]).toHaveClass('winner')
})

test('a tie marks neither score cell', () => {
  const dialog = renderOver({ winner: null, area: [150, 149], score: [150, 149] })
  expect(winnerCell(dialog)).toEqual([null, null])
})

test('a game with no modifier rows has no table, the scoreboard being the whole breakdown', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(within(dialog).queryByRole('table')).not.toBeInTheDocument()
})

test('the scoreboard shows total score, not territory, when modifiers apply', () => {
  const dialog = renderOver({ winner: 1, area: [152, 141], score: [162, 141] }, (game) => {
    withRules(game)
    game.players['1'].houseRules.prize.captured = 1
  })
  const group = within(dialog).getByRole('group', { name: 'Final score' })
  expect(group).toHaveTextContent('162')
  expect(group).not.toHaveTextContent('152')
})

test('no "Score at surrender" caption on a game that was not surrendered', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(within(dialog).queryByText('Score at surrender')).not.toBeInTheDocument()
})

test('each scoreboard cell names its player', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] }, (game) => {
    game.players['1'].name = 'Ada'
    game.players['2'].name = 'Grace'
  })
  expect(within(scoreCell(dialog, '158') as HTMLElement).getByText('Ada')).toBeInTheDocument()
  expect(within(scoreCell(dialog, '141') as HTMLElement).getByText('Grace')).toBeInTheDocument()
})
