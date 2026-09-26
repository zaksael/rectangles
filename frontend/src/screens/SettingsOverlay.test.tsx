import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { makeGame } from '../testUtils/gameFixtures'
import { SettingsOverlay } from './SettingsOverlay'

function renderOverlay(props: Partial<Parameters<typeof SettingsOverlay>[0]> = {}) {
  const onClose = vi.fn()
  render(
    <SettingsOverlay
      game={makeGame({ board: { size: 19, skipLimit: 3 } })}
      series={null}
      opponentLabel="Bot (Greedy)"
      onClose={onClose}
      {...props}
    />,
  )
  return onClose
}

test('shows the match info: opponent, board size and skip limit', () => {
  renderOverlay()

  expect(screen.getByText('Opponent').nextSibling).toHaveTextContent('Bot (Greedy)')
  expect(screen.getByText('Board size').nextSibling).toHaveTextContent('19×19')
  expect(screen.getByText('Skip limit').nextSibling).toHaveTextContent('3')
})

const midSeries = {
  length: 3,
  scores: { '1': 1, '2': 0 },
  gamesPlayed: 1,
  rounds: [],
  isComplete: false,
  winner: null,
}

test('shows the running round progress when reached mid-series', () => {
  renderOverlay({ series: midSeries })

  expect(screen.getByText('Series').nextSibling).toHaveTextContent('Round 2 of 3')
})

test('has no Series row for a single game', () => {
  renderOverlay({ series: null })

  expect(screen.queryByText('Series')).not.toBeInTheDocument()
})

test('lists every house rule as on or off from the match state, read-only', () => {
  const base = makeGame()
  renderOverlay({
    game: makeGame({
      houseRules: {
        ...base.houseRules,
        wildcard: { ...base.houseRules.wildcard, enabled: true },
        walls: { ...base.houseRules.walls, enabled: false },
        steal: { ...base.houseRules.steal, enabled: true },
      },
    }),
  })

  expect(screen.getByText('Wildcard roll').closest('li')).toHaveTextContent('On')
  expect(screen.getByText('Steal').closest('li')).toHaveTextContent('On')
  expect(screen.getByText('Walls').closest('li')).toHaveTextContent('Off')
  expect(screen.getByText('Comeback').closest('li')).toHaveTextContent('Off')
  expect(screen.getAllByRole('listitem')).toHaveLength(9)
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
})

test('Resume closes the overlay', () => {
  const onClose = renderOverlay()

  fireEvent.click(screen.getByRole('button', { name: 'Resume' }))

  expect(onClose).toHaveBeenCalledTimes(1)
})

test('Escape closes the overlay through the same handler', () => {
  const onClose = renderOverlay()

  fireEvent(screen.getByRole('dialog', { hidden: true }), new Event('cancel', { cancelable: true }))

  expect(onClose).toHaveBeenCalledTimes(1)
})

test('summarises the house rules: none enabled, or how many are on', () => {
  const base = makeGame()
  const { unmount } = render(<SettingsOverlay game={base} series={null} opponentLabel="Bot" onClose={vi.fn()} />)
  expect(screen.getByText('No house rules in this match')).toBeInTheDocument()
  expect(screen.queryByRole('list')).not.toBeInTheDocument()
  unmount()

  renderOverlay({
    game: makeGame({
      houseRules: {
        ...base.houseRules,
        wildcard: { ...base.houseRules.wildcard, enabled: true },
        steal: { ...base.houseRules.steal, enabled: true },
      },
    }),
  })
  expect(screen.getByText('2 house rules on')).toBeInTheDocument()
})
