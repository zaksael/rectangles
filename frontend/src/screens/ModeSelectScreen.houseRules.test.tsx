import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { ModeSelectScreen } from './ModeSelectScreen'

// Only Pitfall is "implemented" here; the real registry has none yet.
vi.mock('../houseRules', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../houseRules')>()
  // Mutate in place: implementedHouseRules reads the module's own list.
  for (const rule of actual.HOUSE_RULE_GROUPS.flatMap((g) => g.rules)) {
    rule.implemented = rule.key === 'pitfallEnabled'
  }
  return actual
})

beforeEach(() => localStorage.clear())

function renderWithBot(onStartGame = vi.fn()) {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  return onStartGame
}

test('shows only implemented house rules, and only their groups', () => {
  renderWithBot()

  expect(screen.getAllByRole('checkbox')).toHaveLength(1)
  expect(screen.getByRole('checkbox', { name: 'Pitfall' })).toBeInTheDocument()
  expect(screen.getByText('Special cells')).toBeInTheDocument()
  expect(screen.queryByText('Board setup')).not.toBeInTheDocument()
})

test('Start Game sends only implemented house rules, and toggling one flips it', () => {
  const onStartGame = renderWithBot()

  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
  expect(onStartGame.mock.calls[0][0]).toMatchObject({ pitfallEnabled: true })
  expect(onStartGame.mock.calls[0][0]).not.toHaveProperty('prizeEnabled')

  fireEvent.click(screen.getByRole('checkbox', { name: 'Pitfall' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
  expect(onStartGame.mock.calls[1][0]).toMatchObject({ pitfallEnabled: false })
})

test('Reset to defaults restores an implemented house rule', () => {
  renderWithBot()

  fireEvent.click(screen.getByRole('checkbox', { name: 'Pitfall' }))
  fireEvent.click(screen.getByRole('button', { name: 'Reset to defaults' }))
  fireEvent.click(screen.getByRole('button', { name: 'Reset' }))

  expect(screen.getByRole('checkbox', { name: 'Pitfall' })).toHaveAttribute('aria-checked', 'true')
})
