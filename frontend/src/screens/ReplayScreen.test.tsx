import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { GameWireState, HistoryEntry, ScoreParts } from '../gameTypes'
import { makeGame } from '../fixtures/gameFixtures'
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

test('an all-skips game has nothing to play', () => {
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
