import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, onTestFinished, test, vi } from 'vitest'
import { makeGame, makeSeries } from '../fixtures/gameFixtures'
import { GameOverBar, GameOverOverlay, SeriesResultOverlay } from './GameOverOverlay'

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
  expect(note(/^Steal/)).toContain('capturer +12, opponent −12, per capture')
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
  expect(buttons.map((b) => b.firstChild?.textContent)).toEqual(['View Board', 'New Game'])
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

test('on the overlay, v shows the board and n starts a new game', () => {
  useGuardClock()
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderOver({ winner: 1, area: [158, 141] }, undefined, handlers)

  fireEvent.keyDown(dialog, { key: 'v' })
  expect(handlers.onViewBoard).toHaveBeenCalledTimes(1)
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(dialog, { key: 'n' })
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
})

// A stray N from placement (the shortcut for the next legal spot) must not start a new game the moment the card appears.
const KEY_GUARD_MS = 500

function useGuardClock() {
  vi.useFakeTimers()
  onTestFinished(() => vi.useRealTimers())
}

test('on the overlay, n is ignored until the guard window has passed', () => {
  useGuardClock()
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderOver({ winner: 1, area: [158, 141] }, undefined, handlers)

  fireEvent.keyDown(dialog, { key: 'n' })
  vi.advanceTimersByTime(KEY_GUARD_MS - 1)
  fireEvent.keyDown(dialog, { key: 'n' })
  expect(handlers.onNewGame).not.toHaveBeenCalled()

  vi.advanceTimersByTime(1)
  fireEvent.keyDown(dialog, { key: 'n' })
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
})

test('on the result bar, n is ignored until the guard window has passed', () => {
  useGuardClock()
  const handlers = renderBar()

  fireEvent.keyDown(window, { key: 'n' })
  expect(handlers.onNewGame).not.toHaveBeenCalled()

  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(window, { key: 'n' })
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
})

test('a held n (auto-repeat) never starts a new game, even after the guard window', () => {
  useGuardClock()
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderOver({ winner: 1, area: [158, 141] }, undefined, handlers)

  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(dialog, { key: 'n', repeat: true })

  expect(handlers.onNewGame).not.toHaveBeenCalled()
})

test('a browser combo such as Ctrl+N is left alone on the overlay', () => {
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderOver({ winner: 1, area: [158, 141] }, undefined, handlers)

  fireEvent.keyDown(dialog, { key: 'n', ctrlKey: true })

  expect(handlers.onNewGame).not.toHaveBeenCalled()
})

function renderBar() {
  const handlers = { onViewResult: vi.fn(), onNewGame: vi.fn() }
  render(<GameOverBar game={makeGame({ gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })} {...handlers} />)
  return handlers
}

test('on the result bar, v shows the result and n starts a new game', () => {
  useGuardClock()
  const handlers = renderBar()

  fireEvent.keyDown(window, { key: 'v' })
  expect(handlers.onViewResult).toHaveBeenCalledTimes(1)
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(window, { key: 'n' })
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
})

test('the result bar ignores n and v while another dialog, such as the Menu, is open', () => {
  const handlers = renderBar()
  const menu = document.createElement('dialog')
  menu.setAttribute('open', '')
  document.body.append(menu)

  fireEvent.keyDown(window, { key: 'n' })
  fireEvent.keyDown(window, { key: 'v' })
  menu.remove()

  expect(handlers.onNewGame).not.toHaveBeenCalled()
  expect(handlers.onViewResult).not.toHaveBeenCalled()
})

test('the game-over buttons expose their keyboard shortcuts to assistive tech', () => {
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(within(dialog).getByRole('button', { name: 'View Board' })).toHaveAttribute('aria-keyshortcuts', 'v')
  expect(within(dialog).getByRole('button', { name: 'New Game' })).toHaveAttribute('aria-keyshortcuts', 'n')
  cleanup()

  renderBar()
  expect(screen.getByRole('button', { name: 'View Result' })).toHaveAttribute('aria-keyshortcuts', 'v')
  expect(screen.getByRole('button', { name: 'New Game' })).toHaveAttribute('aria-keyshortcuts', 'n')
})

test('the game-over buttons carry hidden V and N key chips for the held-Shift cue', () => {
  const chip = (button: HTMLElement) => button.querySelector('kbd.key-badge')
  const dialog = renderOver({ winner: 1, area: [158, 141] })
  expect(chip(within(dialog).getByRole('button', { name: 'View Board' }))?.textContent).toBe('V')
  expect(chip(within(dialog).getByRole('button', { name: 'New Game' }))?.textContent).toBe('N')
  cleanup()

  renderBar()
  expect(chip(screen.getByRole('button', { name: 'View Result' }))?.textContent).toBe('V')
  expect(chip(screen.getByRole('button', { name: 'New Game' }))?.textContent).toBe('N')
  expect(screen.getAllByRole('button').flatMap((b) => [...b.querySelectorAll('kbd.key-badge')])).toHaveLength(2)
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

function renderRound(
  { winner, reason = 'boardFull', playerId = null, area, series }: Result & { series: ReturnType<typeof makeSeries> },
  handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn(), onNextRound: vi.fn() },
) {
  const game = makeGame({ gameOver: { reason, playerId, winner } })
  game.players['1'].score = { ...game.players['1'].score, totalArea: area[0], totalScore: area[0] }
  game.players['2'].score = { ...game.players['2'].score, totalArea: area[1], totalScore: area[1] }
  render(<GameOverOverlay game={game} series={series} {...handlers} />)
  return screen.getByRole('dialog')
}

test('a settled series round names its position instead of the end reason', () => {
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries({ gamesPlayed: 2 }) })
  expect(within(dialog).getByText('Round 2 of 3')).toBeInTheDocument()
  expect(within(dialog).queryByText('board settled')).not.toBeInTheDocument()
})

test('a series round that did not settle joins its end reason to the round', () => {
  const dialog = renderRound({ winner: 2, reason: 'surrender', playerId: 1, area: [120, 108], series: makeSeries({ gamesPlayed: 2 }) })
  expect(within(dialog).getByText(/^Round 2 of 3 · Player.1 surrendered$/u)).toBeInTheDocument()
})

test('a single game keeps its end reason and gains no round line', () => {
  const dialog = renderOver({ winner: 1, area: [152, 141] })
  expect(within(dialog).getByText('board settled')).toBeInTheDocument()
  expect(within(dialog).queryByText(/Round \d/u)).not.toBeInTheDocument()
})

test('a round loser who leads the series is marked as leading', () => {
  const dialog = renderRound({ winner: 2, area: [129, 131], series: makeSeries({ gamesPlayed: 2, scores: { '1': 301, '2': 299 } }) })
  expect(within(dialog).getByText('Series 301 · leads')).toBeInTheDocument()
  expect(within(dialog).getByText('Series 299')).toBeInTheDocument()
})

test('equal series totals mark nobody as leading', () => {
  const tied = renderRound({ winner: 1, area: [140, 120], series: makeSeries({ gamesPlayed: 2, scores: { '1': 280, '2': 280 } }) })
  expect(within(tied).getAllByText('Series 280')).toHaveLength(2)
  expect(within(tied).queryByText(/leads/u)).not.toBeInTheDocument()
})

test('a series round is headlined as the round, not the game', () => {
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries() })
  expect(within(dialog).getByRole('heading', { name: /^Player.1 wins the round$/u })).toBeTruthy()
})

test('a tied series round is headlined "Round tied"', () => {
  const dialog = renderRound({ winner: null, area: [120, 120], series: makeSeries() })
  expect(within(dialog).getByRole('heading', { name: 'Round tied' })).toBeTruthy()
})

test('round 1 of a series shows no running total, since it would equal the round score', () => {
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries({ gamesPlayed: 1, scores: { '1': 152, '2': 141 } }) })
  expect(within(dialog).queryByText(/^Series \d/)).toBeNull()
})

test('from round 2 each scoreboard cell carries its series total', () => {
  const dialog = renderRound({ winner: 2, area: [129, 131], series: makeSeries({ gamesPlayed: 2, scores: { '1': 301, '2': 299 } }) })
  const board = within(dialog).getByRole('group', { name: 'Round score' })
  expect(within(board).getByText('Series 301 · leads')).toBeTruthy()
  expect(within(board).getByText('Series 299')).toBeTruthy()
})

test('a series round offers View Board then Next Round, and no New Game', () => {
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries() })
  expect(within(dialog).getAllByRole('button').map((b) => b.textContent?.replace(/[VN]$/, ''))).toEqual(['View Board', 'Next Round'])
})

test('Next Round and the N key both advance the series', () => {
  useGuardClock()
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn(), onNextRound: vi.fn() }
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries() }, handlers)
  fireEvent.click(within(dialog).getByRole('button', { name: /Next Round/ }))
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(dialog, { key: 'n' })
  expect(handlers.onNextRound).toHaveBeenCalledTimes(2)
  expect(handlers.onNewGame).not.toHaveBeenCalled()
})

test('the last round of a series has no Next Round, since the series is over', () => {
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries({ gamesPlayed: 3, isComplete: true }) })
  expect(within(dialog).queryByRole('button', { name: /Next Round/ })).toBeNull()
})

test('the series result bar offers View Result and Next Round, and the headline names the round', () => {
  useGuardClock()
  const handlers = { onViewResult: vi.fn(), onNewGame: vi.fn(), onNextRound: vi.fn() }
  render(<GameOverBar game={makeGame({ gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })} series={makeSeries()} {...handlers} />)
  const bar = screen.getByRole('region', { name: 'Game result' })
  expect(within(bar).getAllByRole('button').map((b) => b.textContent?.replace(/[VN]$/, ''))).toEqual(['View Result', 'Next Round'])
  expect(within(bar).getByText(/^Player.1 wins the round$/u)).toBeTruthy()
  fireEvent.click(within(bar).getByRole('button', { name: /Next Round/ }))
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(window, { key: 'n' })
  expect(handlers.onNextRound).toHaveBeenCalledTimes(2)
  expect(handlers.onNewGame).not.toHaveBeenCalled()
})

test('a series round labels its scoreboard as the round score', () => {
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries() })
  expect(within(dialog).getByRole('group', { name: 'Round score' })).toBeTruthy()
})

test('the last round of a series offers Series Result, which opens the series card instead of sending anything', () => {
  useGuardClock()
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn(), onNextRound: vi.fn(), onSeriesResult: vi.fn() }
  const dialog = renderRound({ winner: 1, area: [152, 141], series: makeSeries({ gamesPlayed: 3, isComplete: true }) }, handlers)
  expect(within(dialog).queryByRole('button', { name: /Next Round/ })).toBeNull()
  fireEvent.click(within(dialog).getByRole('button', { name: /Series Result/ }))
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(dialog, { key: 'n' })
  expect(handlers.onSeriesResult).toHaveBeenCalledTimes(2)
  expect(handlers.onNextRound).not.toHaveBeenCalled()
})

test('after the last round, the round bar offers Series Result in place of Next Round', () => {
  useGuardClock()
  const handlers = { onViewResult: vi.fn(), onNewGame: vi.fn(), onNextRound: vi.fn(), onSeriesResult: vi.fn() }
  render(<GameOverBar game={makeGame({ gameOver: { reason: 'boardFull', playerId: null, winner: 1 } })} series={makeSeries({ gamesPlayed: 3, isComplete: true })} {...handlers} />)
  const bar = screen.getByRole('region', { name: 'Game result' })
  fireEvent.click(within(bar).getByRole('button', { name: /Series Result/ }))
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(window, { key: 'n' })
  expect(within(bar).queryByRole('button', { name: /Next Round/ })).toBeNull()
  expect(handlers.onSeriesResult).toHaveBeenCalledTimes(2)
})

function roundTotals(...totals: [number, number][]) {
  const zero = { '1': 0, '2': 0 }
  return totals.map(([a, b]) => ({ area: zero, prizeCaptured: zero, pitfallCaptured: zero, stealCaptured: zero, total: { '1': a, '2': b } }))
}

function renderSeriesResult(series: ReturnType<typeof makeSeries>, handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }) {
  render(<SeriesResultOverlay game={makeGame()} series={series} {...handlers} />)
  return screen.getByRole('dialog')
}

const wonSeries = makeSeries({
  gamesPlayed: 3,
  isComplete: true,
  winner: 1,
  scores: { '1': 459, '2': 440 },
  rounds: roundTotals([162, 148], [139, 151], [158, 141]),
})

test('the series card names the winner, the margin and the format', () => {
  const dialog = renderSeriesResult(wonSeries)
  expect(within(dialog).getByRole('heading', { name: /^Player.1 wins the series$/u })).toBeTruthy()
  expect(dialog).toHaveAccessibleDescription('by 19 points')
  expect(within(dialog).getByText('3 rounds · most points wins')).toBeTruthy()
})

test('the series card lists each round and ends on the series total', () => {
  const dialog = renderSeriesResult(wonSeries)
  const rows = within(dialog).getAllByRole('row').slice(1).map((row) => Array.from(row.children).map((c) => c.textContent))
  expect(rows).toEqual([
    ['Round 1', '162', '148'],
    ['Round 2', '139', '151'],
    ['Round 3', '158', '141'],
    ['Series total', '459', '440'],
  ])
})

test('a tied series reads "Series tied" with no margin line', () => {
  const dialog = renderSeriesResult(makeSeries({ gamesPlayed: 3, isComplete: true, winner: null, scores: { '1': 465, '2': 465 }, rounds: roundTotals([150, 160], [160, 150], [155, 155]) }))
  expect(within(dialog).getByRole('heading', { name: 'Series tied' })).toBeTruthy()
  expect(dialog).not.toHaveAccessibleDescription()
})

test('the series card offers View Board and New Game, with V and N as shortcuts', () => {
  useGuardClock()
  const handlers = { onNewGame: vi.fn(), onViewBoard: vi.fn() }
  const dialog = renderSeriesResult(wonSeries, handlers)
  expect(within(dialog).getAllByRole('button').map((b) => b.textContent?.replace(/[VN]$/, ''))).toEqual(['View Board', 'New Game'])
  fireEvent.keyDown(dialog, { key: 'v' })
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(dialog, { key: 'n' })
  fireEvent.click(within(dialog).getByRole('button', { name: /View Board/ }))
  expect(handlers.onViewBoard).toHaveBeenCalledTimes(2)
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
})

test('the series bar shows the series outcome and totals, with View Result and New Game but no Next Round or Series Result', () => {
  useGuardClock()
  const handlers = { onViewResult: vi.fn(), onNewGame: vi.fn(), onNextRound: vi.fn(), onSeriesResult: vi.fn() }
  render(<GameOverBar game={makeGame()} series={wonSeries} seriesResult {...handlers} />)
  const bar = screen.getByRole('region', { name: 'Series result' })
  expect(within(bar).getByText(/^Player.1 wins the series$/u)).toBeTruthy()
  expect(bar).toHaveTextContent('459 – 440')
  expect(within(bar).getAllByRole('button').map((b) => b.textContent?.replace(/[VN]$/, ''))).toEqual(['View Result', 'New Game'])
  vi.advanceTimersByTime(KEY_GUARD_MS)
  fireEvent.keyDown(window, { key: 'n' })
  expect(handlers.onNewGame).toHaveBeenCalledTimes(1)
  expect(handlers.onSeriesResult).not.toHaveBeenCalled()
})

test('a tied series bar reads "Series tied"', () => {
  render(<GameOverBar game={makeGame()} series={makeSeries({ isComplete: true, winner: null, scores: { '1': 465, '2': 465 } })} seriesResult onViewResult={vi.fn()} onNewGame={vi.fn()} />)
  expect(within(screen.getByRole('region', { name: 'Series result' })).getByText('Series tied')).toBeTruthy()
})
