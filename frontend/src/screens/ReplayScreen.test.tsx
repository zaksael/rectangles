import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, onTestFinished, test, vi } from 'vitest'
import type { Analysis, AnalysisTurn, GameWireState, HistoryEntry, ScoreParts } from '../game/gameTypes'
import { makeGame, makeHistoryEntry, makeSeries, reach } from '../dev/fixtures/gameFixtures'
import { ReplayScreen } from './ReplayScreen'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

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
  return makeHistoryEntry({ playerId, placed, score: { '1': total(b['1']), '2': total(b['2']) }, breakdown: b, ...extra })
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

test('shows no connection notice while the connection is up', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)

  expect(screen.queryByText(/Connection lost/)).not.toBeInTheDocument()
})

test('the replay still steps and jumps while the connection notice shows', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} connectionLost />)

  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  expect(screen.getByText('Turn 1 of 2')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  expect(screen.getByText('Turn 2 of 2')).toBeTruthy()
})

test('Back still goes back while the connection notice shows', () => {
  const onBack = vi.fn()
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={onBack} connectionLost />)

  fireEvent.click(screen.getByRole('button', { name: 'Back' }))

  expect(onBack).toHaveBeenCalledTimes(1)
})

test('Next places the first move, and only that piece carries the last-piece cue', () => {
  const { container } = render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  expect(screen.getByText('Turn 1 of 2')).toBeTruthy()
  expect(pieces(container)).toHaveLength(1)
  expect(container.querySelectorAll('.piece-outline.last')).toHaveLength(1)
  expect(screen.getByRole('button', { name: 'First' })).toBeEnabled()
})

test('the key listeners are bound once, not again on every step', () => {
  const add = vi.spyOn(window, 'addEventListener')
  onTestFinished(() => add.mockRestore())
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))

  expect(add.mock.calls.filter(([type]) => type === 'keydown')).toHaveLength(1)
  expect(add.mock.calls.filter(([type]) => type === 'keyup')).toHaveLength(1)
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

test('an empty history opens with nothing to step through', () => {
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

test('clicks queued in one batch stop at the last turn and back at the start', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }))
  act(() => {
    click('Next')
    click('Next')
    click('Next')
  })
  expect(screen.getByText('Turn 2 of 2')).toBeTruthy()
  act(() => {
    click('Prev')
    click('Prev')
    click('Prev')
    click('Prev')
  })
  expect(screen.getByText('Start of game')).toBeTruthy()
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
  expect(caption()).toHaveTextContent('Turn 1 of 1Player 1 placed a 3×4 rectangle at row 12, column 8')
})

test('a skip step reads skipped with the roll', () => {
  render(<ReplayScreen game={replayGame([move(2, null, {}, { roll: [3, 4] })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('Player 2 skipped (rolled 3, 4)')
})

test('an all-skips game plays through: every step reads skipped, the board stays empty and the last step names the skip limit', () => {
  const skips = [move(1, null, {}, { roll: [1, 2] }), move(2, null, {}, { roll: [3, 4] }), move(1, null, {}, { roll: [5, 6] }), move(2, null, {}, { roll: [1, 1] })]
  vi.useFakeTimers()
  const { container } = render(
    <ReplayScreen game={replayGame(skips, (g) => { g.gameOver = { ...g.gameOver, reason: 'skipLimit', playerId: 2, winner: 1 } })} onBack={vi.fn()} />,
  )
  expect(screen.getByRole('button', { name: 'Play' })).toBeEnabled()

  fireEvent.click(screen.getByRole('button', { name: 'Play' }))
  act(() => void vi.advanceTimersByTime(600))
  expect(caption()).toHaveTextContent('Turn 1 of 4Player 1 skipped (rolled 1, 2)')
  for (let step = 0; step < 3; step++) act(() => void vi.advanceTimersByTime(600)) // one timer per step, re-armed after each render

  expect(caption()).toHaveTextContent('Turn 4 of 4Player 2 skipped (rolled 1, 1) — Player 2 hit the skip limit (5 of 5)')
  expect(pieces(container)).toHaveLength(0)
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
})

test('a wildcard placement ends with the roll before the edit', () => {
  render(<ReplayScreen game={replayGame([move(1, { topLeft: [0, 0], width: 2, height: 5 }, {}, { wildcardOriginalRoll: [3, 4] })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('Player 1 placed a 2×5 rectangle at row 1, column 1 (wildcard: rolled 3, 4)')
})

test('the caption is a polite live region', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(caption()).toHaveAttribute('aria-live', 'polite')
})

test('a Prize capture is named with its points, and not again on a later step that adds nothing', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4, prize: 5 } }), place(1, [3, 3], 1, 1, { '1': { area: 5, prize: 5 } })])} onBack={vi.fn()} />)
  next()
  expect(caption()).toHaveTextContent('placed a 2×2 rectangle at row 1, column 1 — captures Prize (+5)')
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
  expect(caption()).toHaveTextContent('row 1, column 1 — captures Prize (+5), hits Pitfall (−3)')
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
  expect(lastStepCaption('boardFull', null, 1)).toHaveTextContent('Player 2 skipped (rolled 2, 2) — no room left to build')
  cleanup()
  expect(lastStepCaption('playerBlocked', 2, 1)).toHaveTextContent('— Player 2 had no legal move left')
  cleanup()
  expect(lastStepCaption('skipLimit', 2, 1)).toHaveTextContent('— Player 2 hit the skip limit (5 of 5)')
  cleanup()
  expect(lastStepCaption('surrender', 2, 1)).toHaveTextContent('— Player 2 surrendered, Player 1 wins')
})

const resultCaption = (reason: GameWireState['gameOver']['reason'], winner: number | null, scores: [number, number]) => {
  const last = move(2, null, { '1': { area: scores[0] }, '2': { area: scores[1] } })
  const game = replayGame([place(1, [0, 0], 2, 2), last], (g) => {
    g.gameOver = { ...g.gameOver, reason, playerId: reason === 'boardFull' ? null : 2, winner }
  })
  render(<ReplayScreen game={game} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Last' }))
  return caption()
}

test('the last step follows the end reason with who won by how much, or tied; a surrender names its winner only', () => {
  expect(resultCaption('boardFull', 1, [30, 18])).toHaveTextContent('— no room left to build, Player 1 wins by 12')
  cleanup()
  expect(resultCaption('playerBlocked', 2, [10, 14])).toHaveTextContent('— Player 2 had no legal move left, Player 2 wins by 4')
  cleanup()
  expect(resultCaption('skipLimit', 1, [20, 5])).toHaveTextContent('— Player 2 hit the skip limit (5 of 5), Player 1 wins by 15')
  cleanup()
  expect(resultCaption('boardFull', null, [16, 16])).toHaveTextContent('— no room left to build, tied')
  cleanup()
  expect(resultCaption('surrender', 1, [3, 40])).toHaveTextContent(/— Player 2 surrendered, Player 1 wins$/)
})

test('only the last step carries the end reason', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  next()
  expect(caption()).not.toHaveTextContent('no room left to build')
})

const cellsOf = (label: string) =>
  within(screen.getByRole('rowheader', { name: new RegExp(`^${label}( |$)`) }).closest('tr')!)
    .getAllByRole('cell')
    .map((cell) => cell.textContent)
const rowHeaders = () => screen.getAllByRole('rowheader').map((header) => header.textContent)
const rowLabels = () => rowHeaders().map((h) => h!.replace(/ [+−±]\d+$/, '')) // a special-cell row's label ends with its value
const rulesOn = (...rules: ('prize' | 'pitfall' | 'steal' | 'selfEnclosedPenalty')[]) => (g: GameWireState) => {
  for (const rule of rules) g.houseRules[rule].enabled = true
}

const withPoints = (...kinds: ('prize' | 'pitfall' | 'steal')[]) => (g: GameWireState) => {
  for (const kind of kinds) g.houseRules[kind] = { enabled: true, cells: [], points: 10 }
}

test('a special-cell rule\'s row carries the board\'s mark and what a capture is worth, in rule order', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 1, 1)], withPoints('steal', 'prize', 'pitfall'))} onBack={vi.fn()} />)

  expect(rowHeaders().filter((h) => /Prize|Pitfall|Steal/.test(h!))).toEqual(['Prize +10', 'Pitfall −10', 'Steal ±10'])
  for (const kind of ['prize', 'pitfall', 'steal']) {
    expect(document.querySelector(`.score-table th .rule-mark.board-cell.${kind}`)).toHaveAttribute('aria-hidden', 'true')
  }
})

test('only the rules that are on show a mark, and a rule with no mark of its own stays plain', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 1, 1)], (g) => { withPoints('prize')(g); g.houseRules.selfEnclosedPenalty.enabled = true })} onBack={vi.fn()} />)

  expect(rowHeaders()).toEqual(['Area', 'Prize +10', 'Enclosure', 'Total', 'In reach'])
  expect(document.querySelectorAll('.score-table .rule-mark')).toHaveLength(1)
})

test('the table starts at zero and follows the step: Area and Total per player', () => {
  render(<ReplayScreen game={replayGame([place(1, [0, 0], 2, 2, { '1': { area: 4 } })])} onBack={vi.fn()} />)
  expect(cellsOf('Total')).toEqual(['0', '0'])
  next()
  expect(cellsOf('Area')).toEqual(['4', '0'])
  expect(cellsOf('Total')).toEqual(['4', '0'])
})

test('a rule gets a row only when it is on, and In reach always follows Total', () => {
  const history = [place(1, [0, 0], 2, 2, { '1': { area: 4 } })]
  render(<ReplayScreen game={replayGame(history)} onBack={vi.fn()} />)
  expect(rowLabels()).toEqual(['Area', 'Total', 'In reach'])
  cleanup()
  render(<ReplayScreen game={replayGame(history, rulesOn('prize'))} onBack={vi.fn()} />)
  expect(rowLabels()).toEqual(['Area', 'Prize', 'Total', 'In reach'])
  cleanup()
  render(<ReplayScreen game={replayGame(history, rulesOn('prize', 'pitfall', 'steal', 'selfEnclosedPenalty'))} onBack={vi.fn()} />)
  expect(rowLabels()).toEqual(['Area', 'Prize', 'Pitfall', 'Steal', 'Enclosure', 'Total', 'In reach'])
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
  const [mine, theirs] = within(screen.getByRole('rowheader', { name: /^Prize/ }).closest('tr')!).getAllByRole('cell')
  expect(mine).not.toHaveClass('zero')
  expect(theirs).toHaveClass('zero')
})

test('In reach is the last row, under Total, and shows each player\'s reachable cells at the step', () => {
  const history = [place(1, [0, 0], 2, 2), place(2, [3, 3], 2, 2)].map((entry, i) => ({ ...entry, potential: reach(21 - 2 * i, 20 - 3 * i) }))
  render(<ReplayScreen game={replayGame(history)} onBack={vi.fn()} />)
  next()
  expect(cellsOf('In reach')).toEqual(['21', '20'])
  expect(rowLabels().at(-1)).toBe('In reach')
  next()
  expect(cellsOf('In reach')).toEqual(['19', '17'])
})

test('at the start of the game In reach has no figure: a muted en dash per player', () => {
  render(<ReplayScreen game={replayGame([{ ...place(1, [0, 0], 2, 2), potential: reach(21, 20) }])} onBack={vi.fn()} />)
  expect(cellsOf('In reach')).toEqual(['–', '–'])
  for (const cell of within(screen.getByRole('rowheader', { name: 'In reach' }).closest('tr')!).getAllByRole('cell')) expect(cell).toHaveClass('zero')
  next()
  for (const cell of within(screen.getByRole('rowheader', { name: 'In reach' }).closest('tr')!).getAllByRole('cell')) expect(cell).not.toHaveClass('zero')
})

test('In reach is explained by a line under it, at the start of the game as well as mid-game', () => {
  render(<ReplayScreen game={replayGame([{ ...place(1, [0, 0], 2, 2), potential: reach(21, 20) }])} onBack={vi.fn()} />)
  const note = 'Cells each could still build on; counts overlap'
  expect(screen.getByText(note)).toBeVisible()
  expect(screen.getByRole('rowheader', { name: 'In reach' })).toHaveAccessibleDescription(note)
  next()
  expect(screen.getByRole('rowheader', { name: 'In reach' })).toHaveAccessibleDescription(note)
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

test('both header dots are filled at every step: the .over class keeps Playing\'s ring rule off a replay, which has no mover', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  for (const header of screen.getAllByRole('columnheader')) expect(header).toHaveClass('over')
})

test('the screen is a main landmark and the rail a named complementary one', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)

  const main = screen.getByRole('main')
  expect(within(main).getByRole('complementary', { name: 'Replay controls' })).toBeInTheDocument()
})

test('a series round names its round and the series score on two rows beside the title; a single game shows neither', () => {
  const series = makeSeries({ gamesPlayed: 2, length: 3, scores: { '1': 1, '2': 1 } })
  const { unmount } = render(<ReplayScreen game={replayGame(TWO_MOVES)} series={series} onBack={vi.fn()} />)
  const round = screen.getByText('Round 2 of 3')
  const seriesScore = screen.getByText('Series 1 – 1')
  expect(round.parentElement).toBe(seriesScore.parentElement)
  expect(screen.getByRole('heading', { level: 1, name: 'Replay' }).parentElement).toHaveTextContent('ReplayRound 2 of 3Series 1 – 1Back')
  unmount()

  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(screen.getByRole('heading', { level: 1, name: 'Replay' }).parentElement).toHaveTextContent(/^ReplayBack$/)
})

test('the keys the screen answers to are named under the controls', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)

  expect(screen.getByText('Arrows step, Home/End jump, Space plays, Esc goes back')).toBeInTheDocument()
})

test('the opponent is named in the table header as on Playing', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES, (g) => { g.players['2'].name = 'Bot (hard)' })} onBack={vi.fn()} />)
  expect(screen.getByRole('columnheader', { name: 'Bot (hard)' })).toBeTruthy()
})

const THREE_MOVES = [place(1, [0, 0], 2, 2), place(2, [3, 3], 2, 2), place(1, [0, 3], 1, 1)]
const click = (name: string) => fireEvent.click(screen.getByRole('button', { name }))
const tick = (ms: number) => act(() => void vi.advanceTimersByTime(ms))
const renderPlaying = (history = THREE_MOVES) => {
  vi.useFakeTimers()
  return render(<ReplayScreen game={replayGame(history)} onBack={vi.fn()} />)
}

test('Play sits between Prev and Next, turns into Pause and steps once a Normal interval later', () => {
  renderPlaying()
  expect(within(document.querySelector('.transport')!).getAllByRole('button').map((b) => b.textContent)).toEqual(['First', 'Prev', 'Play', 'Next', 'Last'])
  click('Play')
  expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  tick(599)
  expect(caption()).toHaveTextContent('Start of game')
  tick(1)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
})

test('speed buttons are a labelled group of toggles with Normal pressed, and Slow and Fast set 1200 and 250 ms', () => {
  renderPlaying()
  const group = screen.getByRole('group', { name: 'Playback speed' })
  expect(within(group).getAllByRole('button').map((b) => [b.textContent, b.getAttribute('aria-pressed')])).toEqual([['Slow', 'false'], ['Normal', 'true'], ['Fast', 'false']])
  click('Slow')
  expect(screen.getByRole('button', { name: 'Slow' })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByRole('button', { name: 'Normal' })).toHaveAttribute('aria-pressed', 'false')
  click('Play')
  tick(1199)
  expect(caption()).toHaveTextContent('Start of game')
  tick(1)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
  click('Fast')
  tick(250)
  expect(caption()).toHaveTextContent('Turn 2 of 3')
})

test('playback runs every step at the same pace, skips included, stops on the last one and does not loop', () => {
  renderPlaying([place(1, [0, 0], 2, 2), move(2, null), place(1, [3, 3], 1, 1)])
  click('Play')
  tick(600)
  tick(600)
  expect(caption()).toHaveTextContent('Turn 2 of 3')
  tick(600)
  expect(caption()).toHaveTextContent('Turn 3 of 3')
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  tick(10_000)
  expect(caption()).toHaveTextContent('Turn 3 of 3')
})

test('a window that goes too narrow pauses autoplay, and widening again leaves it paused', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  fireEvent.click(screen.getByRole('button', { name: 'Play' }))
  expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  const setWidth = (width: number) => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
    act(() => {
      window.dispatchEvent(new Event('resize'))
    })
  }
  setWidth(1000)
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  setWidth(1400)
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
})

test('Pause stops the stepping', () => {
  renderPlaying()
  click('Play')
  tick(600)
  click('Pause')
  tick(10_000)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
})

test.each(['First', 'Prev', 'Next', 'Last'])('%s pauses autoplay', (name) => {
  renderPlaying()
  click('Next')
  click('Play')
  click(name)
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  const shown = caption().textContent
  tick(10_000)
  expect(caption().textContent).toBe(shown)
})

test('Play on the last step starts again from the first', () => {
  renderPlaying()
  click('Last')
  click('Play')
  expect(caption()).toHaveTextContent('Start of game')
  expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  tick(600)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
})

test('changing the speed while playing restarts the wait at the new interval', () => {
  renderPlaying()
  click('Play')
  tick(500)
  click('Fast')
  tick(249)
  expect(caption()).toHaveTextContent('Start of game')
  tick(1)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
})

test('an empty history has nothing to play', () => {
  renderPlaying([])
  expect(screen.getByRole('button', { name: 'Play' })).toBeDisabled()
})

const press = (key: string, init: KeyboardEventInit = {}) => fireEvent.keyDown(document.body, { key, ...init })

test.each([
  ['ArrowRight', 'Turn 1 of 3'],
  ['ArrowDown', 'Turn 1 of 3'],
  ['End', 'Turn 3 of 3'],
])('%s steps forward from the start', (key, shown) => {
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  press(key)
  expect(caption()).toHaveTextContent(shown)
})

test.each([
  ['ArrowLeft', 'Turn 1 of 3'],
  ['ArrowUp', 'Turn 1 of 3'],
  ['Home', 'Start of game'],
])('%s steps back from turn 2', (key, shown) => {
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  click('Next')
  click('Next')
  press(key)
  expect(caption()).toHaveTextContent(shown)
})

test('keys stop at either end instead of running past it', () => {
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  press('ArrowLeft')
  expect(caption()).toHaveTextContent('Start of game')
  press('End')
  press('ArrowRight')
  expect(caption()).toHaveTextContent('Turn 3 of 3')
})

test('Space plays and pauses', () => {
  vi.useFakeTimers()
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  press(' ')
  expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  tick(600)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
  press(' ')
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
})

test('a step key pauses autoplay', () => {
  vi.useFakeTimers()
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  press(' ')
  press('ArrowRight')
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  tick(10_000)
  expect(caption()).toHaveTextContent('Turn 1 of 3')
})

test('Escape goes back', () => {
  const onBack = vi.fn()
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={onBack} />)
  press('Escape')
  expect(onBack).toHaveBeenCalledOnce()
})

test('Space on a focused button plays instead of also pressing that button', () => {
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  const nextButton = screen.getByRole('button', { name: 'Next' })
  nextButton.focus()
  const notPrevented = fireEvent.keyDown(nextButton, { key: ' ' })
  expect(notPrevented).toBe(false)
  expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
  expect(fireEvent.keyUp(nextButton, { key: ' ' })).toBe(false)
})

test('browser shortcuts with Ctrl, Cmd or Alt are left alone', () => {
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  for (const modifier of ['ctrlKey', 'metaKey', 'altKey']) press('ArrowRight', { [modifier]: true })
  expect(caption()).toHaveTextContent('Start of game')
})

test('Space does nothing in a game with no moves', () => {
  render(<ReplayScreen game={replayGame([])} onBack={vi.fn()} />)
  press(' ')
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
})

test('the rail charts the score history, and the chart marker follows the step', () => {
  const { container } = render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(screen.getByText('Score history', { selector: '.chart-label' })).toBeTruthy()
  const marker = () => container.querySelector('line.chart-marker')!.getAttribute('x1')
  expect(marker()).toBe('36')
  next()
  expect(marker()).toBe('173')
})

test('a game with no moves charts nothing', () => {
  render(<ReplayScreen game={replayGame([])} onBack={vi.fn()} />)
  expect(screen.getByText('Nothing to chart: no moves were played')).toBeTruthy()
})

const jumpTargets = () => screen.getAllByRole('button', { name: /^Jump to turn/ })

test('clicking a turn on the chart jumps there and stops autoplay', () => {
  vi.useFakeTimers()
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  click('Play')
  fireEvent.click(jumpTargets()[2])
  expect(caption()).toHaveTextContent('Turn 2 of 3')
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  tick(10_000)
  expect(caption()).toHaveTextContent('Turn 2 of 3')
})

test('with focus on the chart, arrows move around it instead of stepping the replay', () => {
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={vi.fn()} />)
  jumpTargets()[0].focus()
  fireEvent.keyDown(jumpTargets()[0], { key: 'ArrowRight' })
  expect(jumpTargets()[1]).toHaveFocus()
  expect(caption()).toHaveTextContent('Start of game')
  fireEvent.keyDown(jumpTargets()[1], { key: 'Enter' })
  expect(caption()).toHaveTextContent('Turn 1 of 3')
})

test('Space on the chart jumps instead of playing, and Escape still goes back', () => {
  const onBack = vi.fn()
  render(<ReplayScreen game={replayGame(THREE_MOVES)} onBack={onBack} />)
  jumpTargets()[2].focus()
  fireEvent.keyDown(jumpTargets()[2], { key: ' ' })
  expect(caption()).toHaveTextContent('Turn 2 of 3')
  expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy()
  fireEvent.keyDown(jumpTargets()[2], { key: 'Escape' })
  expect(onBack).toHaveBeenCalledOnce()
})

test('the chart names the opponent as the rest of the screen does', () => {
  render(<ReplayScreen game={replayGame(THREE_MOVES, (g) => { g.players['2'].name = 'Bot (hard)' })} onBack={vi.fn()} />)
  expect(screen.getByRole('group', { name: 'Score history, Player 1 and Bot (hard)' })).toBeTruthy()
})

test('the score table carries the shared score-table class', () => {
  render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={vi.fn()} />)
  expect(screen.getByRole('table').classList.contains('score-table')).toBe(true)
})


// --- turn analysis ---

const flagged = (overrides: Partial<AnalysisTurn> = {}): AnalysisTurn => ({
  turn: 1, axis: 'prize', chosen: 0, best: 10, topLeft: [0, 0], width: 4, height: 1, ...overrides,
})
const ready = (...turns: AnalysisTurn[]): Analysis => ({ status: 'ready', turns })
const renderAnalysed = (analysis: Analysis | null, step = 0) => {
  const view = render(<ReplayScreen game={replayGame(TWO_MOVES)} onBack={() => {}} analysis={analysis} />)
  for (let i = 0; i < step; i++) fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  return view
}

test('a flagged turn gets a note naming the points and the axis, with a real minus sign', () => {
  renderAnalysed(ready(flagged({ chosen: -10, best: 10 })), 1)

  expect(screen.getByText('Scored −10 this turn; the best move scored 10 (Prize)')).toBeTruthy()
})

test('a steal turn names the Steal axis in points', () => {
  renderAnalysed(ready(flagged({ axis: 'steal', chosen: 0, best: 10 })), 1)

  expect(screen.getByText('Scored 0 this turn; the best move scored 10 (Steal)')).toBeTruthy()
})

test('a denial turn reads in cells, singular for one', () => {
  renderAnalysed(ready(flagged({ axis: 'denial', chosen: 1, best: 5 })), 1)

  expect(screen.getByText('Denied 1 cell this turn; the best move denied 5')).toBeTruthy()
})

test('a denial turn with several cells reads plural', () => {
  renderAnalysed(ready(flagged({ axis: 'denial', chosen: 5, best: 25 })), 1)

  expect(screen.getByText('Denied 5 cells this turn; the best move denied 25')).toBeTruthy()
})

test('a turn that is not flagged has no note, with other turns flagged', () => {
  renderAnalysed(ready(flagged({ turn: 2 })), 1)

  expect(screen.queryByText(/this turn; the best move/)).toBeNull()
})

test('while the analysis loads the note slot says it is checking, as a status', () => {
  renderAnalysed({ status: 'loading' }, 1)

  expect(screen.getByRole('status').textContent).toBe('Checking for better moves…')
})

test('an unavailable analysis says so and Replay still steps', () => {
  renderAnalysed({ status: 'unavailable' }, 1)

  expect(screen.getByText('Turn analysis unavailable')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Next' })).toBeTruthy()
})

test('a game with nothing flagged says none were found on every step', () => {
  renderAnalysed(ready(), 1)

  expect(screen.getByText('No better moves found')).toBeTruthy()
})

test('no analysis asked for shows nothing in the note slot', () => {
  renderAnalysed(null, 1)

  expect(screen.queryByText(/better moves|Turn analysis|this turn; the best/)).toBeNull()
})


test('flagged turns ring the chart and the chart says what a ring means', () => {
  const { container } = renderAnalysed(ready(flagged({ turn: 1 })), 1)

  expect(container.querySelectorAll('.chart-ring')).toHaveLength(1)
  expect(screen.getByText('Better move existed')).toBeTruthy()
})

const renderToggle = (props: { showBetterOption?: boolean; onToggle?: () => void; turn?: AnalysisTurn } = {}) => {
  const view = render(
    <ReplayScreen
      game={replayGame(TWO_MOVES)}
      onBack={() => {}}
      analysis={ready(props.turn ?? flagged({ topLeft: [1, 2], width: 3, height: 2 }))}
      showBetterOption={props.showBetterOption}
      onToggleBetterOption={props.onToggle}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  return view
}
const toggle = () => screen.queryByRole('button', { name: 'Show Better Option' })
const outline = (container: HTMLElement) => container.querySelector('.better-option') as HTMLElement | null

test('a flagged turn offers Show Better Option, not pressed by default', () => {
  renderToggle()

  expect(toggle()?.getAttribute('aria-pressed')).toBe('false')
})

test('a turn that is not flagged has no toggle', () => {
  renderToggle({ turn: flagged({ turn: 2 }) })

  expect(toggle()).toBeNull()
})

test('pressing the toggle asks the owner of the state to flip it', () => {
  const onToggle = vi.fn()
  renderToggle({ onToggle })

  fireEvent.click(toggle()!)

  expect(onToggle).toHaveBeenCalledTimes(1)
})

test('with it on, the toggle reads pressed and the better placement is outlined on the board', () => {
  const { container } = renderToggle({ showBetterOption: true })
  const box = outline(container)!

  expect(toggle()?.getAttribute('aria-pressed')).toBe('true')
  expect(['--r', '--c', '--w', '--h'].map((v) => box.style.getPropertyValue(v))).toEqual(['1', '2', '3', '2'])
})

test('with it off there is no outline', () => {
  const { container } = renderToggle({ showBetterOption: false })

  expect(outline(container)).toBeNull()
})

test('with it on, stepping to a turn that is not flagged drops the outline and the button', () => {
  const { container } = renderToggle({ showBetterOption: true })

  fireEvent.click(screen.getByRole('button', { name: 'Next' }))

  expect(outline(container)).toBeNull()
  expect(toggle()).toBeNull()
})

test('a note over 50 characters puts the toggle on its own row', () => {
  const { container } = renderToggle({ turn: flagged({ axis: 'enclosure', chosen: -100, best: 100 }) })

  expect(container.querySelector('.analysis-row.stacked')).not.toBeNull()
})

test('a shorter note keeps the toggle beside it', () => {
  const { container } = renderToggle({ turn: flagged({ axis: 'denial', chosen: 5, best: 25 }) })

  expect(container.querySelector('.analysis-row')).not.toBeNull()
  expect(container.querySelector('.analysis-row.stacked')).toBeNull()
})
