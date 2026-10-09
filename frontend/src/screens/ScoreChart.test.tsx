import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { HistoryEntry } from '../gameTypes'
import { ScoreChart } from './ScoreChart'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const zero = { area: 0, prize: 0, pitfall: 0, steal: 0, enclosure: 0 }
const entry = (one: number, two: number): HistoryEntry => ({
  playerId: 1,
  roll: [1, 1],
  placed: null,
  wildcardOriginalRoll: null,
  score: { '1': one, '2': two },
  breakdown: { '1': zero, '2': zero },
})

// Scores per turn after turn 0; the chart is 320x300 here, so the plot runs x 36..310 and y 274 (bottom) to 10 (top).
const NAMES = { '1': 'Player 1', '2': 'Player 2' }
const draw = (scores: [number, number][], step = 0, onJump: (turn: number) => void = () => {}, names = NAMES) =>
  render(<ScoreChart history={scores.map(([a, b]) => entry(a, b))} step={step} names={names} onJump={onJump} />)
// Y labels sit right-aligned at x=24 (12px left of the plot), turn numbers along y=292 (8px above the bottom).
const yLabels = (container: HTMLElement) => [...container.querySelectorAll('svg text[x="24"]')].map((t) => t.textContent)
const turnLabels = (container: HTMLElement) => [...container.querySelectorAll('svg text[y="292"]')].map((t) => t.textContent)
const points = (container: HTMLElement, selector: string) => container.querySelector(selector)?.getAttribute('points')

// Player 1 climbs 0, 25, 50 and Player 2 0, 0, 25: a top of 50 puts 0 at y=274, 25 at y=142, 50 at y=10.
const CLIMB: [number, number][] = [[25, 0], [50, 25]]

test('a game with no moves says there is nothing to chart, and draws no chart', () => {
  const { container } = draw([])
  expect(screen.getByText('Nothing to chart: no moves were played')).toBeTruthy()
  expect(container.querySelector('svg')).toBeNull()
})

test('the y axis counts up in 25s to the best score rounded up, and is at least 25 tall', () => {
  expect(yLabels(draw(CLIMB).container)).toEqual(['0', '25', '50'])
  cleanup()
  expect(yLabels(draw([[3, 1]]).container)).toEqual(['0', '25'])
})

test('a score below zero extends the axis down in 25s, and only then is the zero line drawn in ink', () => {
  const { container } = draw([[25, -3]])
  expect(yLabels(container)).toEqual(['−25', '0', '25'])
  const zeroLine = container.querySelector('line[y1="142"]')!
  expect(zeroLine).toHaveAttribute('stroke', 'var(--ink)')
  expect(container.querySelector('line[y1="274"]')).toHaveAttribute('stroke', 'var(--line)')
  cleanup()
  const { container: positive } = draw(CLIMB)
  expect(positive.querySelector('line[y1="274"]')).toHaveAttribute('stroke', 'var(--line)')
})

test('turn numbers run every 5 turns and at the last turn', () => {
  const twelve = Array.from({ length: 12 }, (): [number, number] => [0, 0])
  expect(turnLabels(draw(twelve).container)).toEqual(['0', '5', '10', '12'])
  cleanup()
  expect(turnLabels(draw([[0, 0], [0, 0], [0, 0]]).container)).toEqual(['0', '3'])
})

test('each line is solid up to the current turn and faded after it', () => {
  const { container } = draw(CLIMB, 1)
  expect(points(container, '.chart-line.p1.played')).toBe('36,274 173,142')
  expect(points(container, '.chart-line.p1.ahead')).toBe('173,142 310,10')
  expect(points(container, '.chart-line.p2.played')).toBe('36,274 173,274')
  expect(points(container, '.chart-line.p2.ahead')).toBe('173,274 310,142')
  expect(container.querySelector('.chart-line.p1.ahead')).toHaveAttribute('opacity', '0.35')
  expect(container.querySelector('.chart-line.p1.played')).toHaveAttribute('stroke', 'var(--p1)')
  expect(container.querySelector('.chart-line.p2.played')).toHaveAttribute('stroke', 'var(--p2)')
})

test('at the start nothing is played yet, and at the end nothing is left', () => {
  const start = draw(CLIMB, 0).container
  expect(start.querySelector('.chart-line.played')).toBeNull()
  expect(points(start, '.chart-line.p1.ahead')).toBe('36,274 173,142 310,10')
  cleanup()
  const end = draw(CLIMB, 2).container
  expect(end.querySelector('.chart-line.ahead')).toBeNull()
  expect(points(end, '.chart-line.p1.played')).toBe('36,274 173,142 310,10')
})

test('a skip step draws flat: the same score twice is the same height', () => {
  const { container } = draw([[25, 0], [25, 0]], 2)
  expect(points(container, '.chart-line.p1.played')).toBe('36,274 173,10 310,10') // the top is 25 here, so 25 sits at y=10
})

test('every turn has a dot per player, the current one is larger and later ones are faded', () => {
  const { container } = draw(CLIMB, 1)
  const dots = (player: string) => [...container.querySelectorAll(`.chart-dot.${player}`)].map((c) => [c.getAttribute('cx'), c.getAttribute('r'), c.getAttribute('opacity')])
  // Turn 0 dots sit 3px apart so they do not hide each other.
  expect(dots('p1')).toEqual([['33', '2.5', '1'], ['173', '5', '1'], ['310', '2.5', '0.35']])
  expect(dots('p2')).toEqual([['39', '2.5', '1'], ['173', '5', '1'], ['310', '2.5', '0.35']])
})

test('a vertical ink marker stands on the current turn', () => {
  const marker = draw(CLIMB, 1).container.querySelector('line.chart-marker')!
  expect(marker).toHaveAttribute('x1', '173')
  expect(marker).toHaveAttribute('x2', '173')
  expect(marker).toHaveAttribute('stroke', 'var(--ink)')
})

test('the chart is a group that names both players, and its axis numbers are hidden from screen readers', () => {
  const { container } = draw(CLIMB)
  expect(screen.getByRole('group', { name: 'Score history, Player 1 and Player 2' })).toBeTruthy()
  expect(container.querySelectorAll('svg text:not([aria-hidden="true"])')).toHaveLength(0)
})

test('the chart is drawn at the size its box reports', () => {
  let report: ResizeObserverCallback = () => {}
  vi.stubGlobal('ResizeObserver', class { constructor(cb: ResizeObserverCallback) { report = cb } observe() {} disconnect() {} unobserve() {} })
  const { container } = draw(CLIMB, 1)
  act(() => report([{ contentRect: { width: 280, height: 200 } } as ResizeObserverEntry], {} as ResizeObserver))
  expect(container.querySelector('svg')).toHaveAttribute('viewBox', '0 0 280 200')
})

const targets = () => screen.getAllByRole('button', { name: /^Jump to turn/ })
const key = (target: Element, name: string) => fireEvent.keyDown(target, { key: name })

test('every turn, the start included, has a jump target that says both scores', () => {
  draw(CLIMB)
  expect(targets().map((t) => t.getAttribute('aria-label'))).toEqual([
    'Jump to turn 0, Player 1 0, Player 2 0',
    'Jump to turn 1, Player 1 25, Player 2 0',
    'Jump to turn 2, Player 1 50, Player 2 25',
  ])
})

test('a bot is named in the jump targets and the group', () => {
  draw(CLIMB, 0, () => {}, { '1': 'Player 1', '2': 'Bot (hard)' })
  expect(targets()[1]).toHaveAccessibleName('Jump to turn 1, Player 1 25, Bot (hard) 0')
  expect(screen.getByRole('group', { name: 'Score history, Player 1 and Bot (hard)' })).toBeTruthy()
})

test('clicking a turn jumps to it', () => {
  const onJump = vi.fn()
  draw(CLIMB, 0, onJump)
  fireEvent.click(targets()[2])
  expect(onJump).toHaveBeenCalledWith(2)
})

test('the chart is one tab stop, on the current turn', () => {
  draw(CLIMB, 1)
  expect(targets().map((t) => t.getAttribute('tabindex'))).toEqual(['-1', '0', '-1'])
  expect(targets()[1]).toHaveAttribute('aria-current', 'true')
  expect(targets()[0]).not.toHaveAttribute('aria-current')
})

test('arrow keys move focus between turns without jumping, and the tab stop goes with the focus', () => {
  const onJump = vi.fn()
  draw(CLIMB, 1, onJump)
  targets()[1].focus()
  key(targets()[1], 'ArrowRight')
  expect(targets()[2]).toHaveFocus()
  expect(targets().map((t) => t.getAttribute('tabindex'))).toEqual(['-1', '-1', '0'])
  key(targets()[2], 'ArrowLeft')
  key(targets()[1], 'ArrowUp')
  expect(targets()[0]).toHaveFocus()
  key(targets()[0], 'ArrowDown')
  expect(targets()[1]).toHaveFocus()
  key(targets()[1], 'End')
  expect(targets()[2]).toHaveFocus()
  key(targets()[2], 'Home')
  expect(targets()[0]).toHaveFocus()
  expect(onJump).not.toHaveBeenCalled()
})

test('the arrows stop at either end', () => {
  draw(CLIMB, 0)
  targets()[0].focus()
  key(targets()[0], 'ArrowLeft')
  expect(targets()[0]).toHaveFocus()
  key(targets()[0], 'End')
  key(targets()[2], 'ArrowRight')
  expect(targets()[2]).toHaveFocus()
})

test('Enter and Space jump to the focused turn', () => {
  const onJump = vi.fn()
  draw(CLIMB, 0, onJump)
  targets()[2].focus()
  key(targets()[2], 'Enter')
  key(targets()[2], ' ')
  expect(onJump.mock.calls).toEqual([[2], [2]])
})

test('leaving the chart gives the tab stop back to the current turn', () => {
  draw(CLIMB, 1)
  targets()[1].focus()
  key(targets()[1], 'ArrowRight')
  act(() => targets()[2].blur())
  expect(targets().map((t) => t.getAttribute('tabindex'))).toEqual(['-1', '0', '-1'])
})

test('the header carries the hint and a readout of both scores and the turn', () => {
  const { container } = draw(CLIMB, 1)
  expect(screen.getByText('Select a turn to jump to it')).toBeTruthy()
  const readout = container.querySelector('.chart-readout')!
  expect(readout).toHaveTextContent('Player 1 25')
  expect(readout).toHaveTextContent('Player 2 0')
  expect(readout).toHaveTextContent('Turn 1')
})

test('a game with no moves has neither the hint nor the readout', () => {
  const { container } = draw([])
  expect(screen.queryByText('Select a turn to jump to it')).toBeNull()
  expect(container.querySelector('.chart-readout')).toBeNull()
})
