import { cleanup, fireEvent, screen, within } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { deadRoll, makeState, renderPlaying, renderScreen, rerollState, rowValues, scoreTable } from '../dev/testUtils/playingScreenHarness'

test('Reroll carries an E key chip', () => {
  const game = deadRoll(1)
  game.houseRules.reroll = { enabled: true, canReroll: true }
  renderScreen({ game, series: null })

  expect(screen.getByRole('button', { name: 'Reroll' }).querySelector('kbd.key-badge')?.textContent).toBe('E')
})

const wildcardState = ({
  editableIndex,
  legalValues,
  currentPlayerId = 1,
}: {
  editableIndex: 0 | 1
  legalValues: number[]
  currentPlayerId?: number
}) => {
  const state = makeState({ turn: { recentTurns: [], currentPlayerId, turnState: 'choosingWildcard', lastRoll: [4, 4], legalPlacements: [] } })
  state.game.houseRules.wildcard = { enabled: true, originalRoll: [4, 4], legalValues, editableIndex }
  return state
}

const pillNames = () => within(screen.getByRole('group', { name: 'Wildcard value' })).getAllByRole('button').map((b) => b.textContent)

test('choosing a wildcard shows the fixed die and a pill for each value 1-6, in place of the dice', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3, 4, 5, 6] }))

  expect(pillNames()).toEqual(['1', '2', '3', '4', '5', '6'])
  expect(screen.getByTestId('wildcard-fixed-die')).toHaveTextContent('4')
  expect(screen.queryByRole('img', { name: /rolled/i })).not.toBeInTheDocument()
})

test('the fixed die is exposed by name so a screen reader hears the number the pills pair with', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3] }))

  expect(screen.getByRole('img', { name: 'Fixed die 4' })).toBeInTheDocument()
})

test('each pill is named for what it sets, not only its digit', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3, 4, 5, 6] }))

  expect(within(screen.getByRole('group', { name: 'Wildcard value' })).getByRole('button', { name: 'Set wildcard die to 3' })).toHaveTextContent('3')
})

test('values with no legal placement are disabled, not removed', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 3, 4, 6] }))

  const group = screen.getByRole('group', { name: 'Wildcard value' })
  for (const [name, enabled] of [['1', true], ['2', false], ['3', true], ['4', true], ['5', false], ['6', true]] as const) {
    const pill = within(group).getByRole('button', { name: `Set wildcard die to ${name}` })
    expect({ name, disabled: pill.matches(':disabled') }).toEqual({ name, disabled: !enabled })
  }
})

test('clicking a pill sends chooseWildcard with that value straight away', () => {
  const sendAction = renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 3, 4, 6] }))

  fireEvent.click(screen.getByRole('button', { name: 'Set wildcard die to 3' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'chooseWildcard', value: 3 })
})

test.each([0, 1] as const)('editableIndex %i: the pills take the wildcard die\'s slot', (editableIndex) => {
  renderScreen(wildcardState({ editableIndex, legalValues: [1, 2, 3, 4, 5, 6] }))

  const picker = screen.getByTestId('wildcard-fixed-die').parentElement!
  const isPillsFirst = picker.firstElementChild!.getAttribute('role') === 'group'
  expect(isPillsFirst).toBe(editableIndex === 0)
})

test('the wildcard turn status describes the pick and the key hint stays blank', () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3] }))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: wildcard roll — pick the other die’s value')
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test('a wildcard roll where no value fits skips the picker and goes straight to Skip', () => {
  const state = makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'skipped', lastRoll: [4, 4], legalPlacements: [] } })
  state.game.houseRules.wildcard = { enabled: true, originalRoll: [4, 4], legalValues: [], editableIndex: null }
  renderScreen(state)

  expect(screen.queryByRole('group', { name: 'Wildcard value' })).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled()
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skipping… (S)')
})

test("on the bot's turn a pending wildcard shows plain dice and no picker", () => {
  renderScreen(wildcardState({ editableIndex: 1, legalValues: [1, 2, 3], currentPlayerId: 2 }), vi.fn(), null, vi.fn(), 2)

  expect(screen.queryByRole('group', { name: 'Wildcard value' })).not.toBeInTheDocument()
  expect(screen.getByRole('img', { name: /rolled 4 and 4/i })).toBeInTheDocument()
})

test('there is no Reroll button when the house rule is off', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(screen.queryByRole('button', { name: 'Reroll' })).not.toBeInTheDocument()
})

test('shows an enabled Reroll button with charges remaining, which sends the reroll action', () => {
  const sendAction = renderScreen(rerollState(true))

  fireEvent.click(screen.getByRole('button', { name: 'Reroll' }))

  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test('hides Reroll once charges are exhausted', () => {
  renderScreen(rerollState(false))

  expect(screen.queryByRole('button', { name: 'Reroll' })).not.toBeInTheDocument()
})

test('Reroll stays enabled alongside a forced Skip', () => {
  renderScreen(rerollState(true, 'skipped'))

  expect(screen.getByRole('button', { name: 'Reroll' })).toBeEnabled()
})

test('Reroll is available while choosing a wildcard value, and E rerolls', () => {
  const state = wildcardState({ editableIndex: 1, legalValues: [1, 2, 3] })
  state.game.houseRules.reroll = { enabled: true, canReroll: true }
  const sendAction = renderScreen(state)

  expect(screen.getByRole('button', { name: 'Reroll' })).toBeEnabled()
  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: wildcard roll — pick the other die’s value, or reroll (E)')
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
  fireEvent.keyDown(window, { key: 'e' })
  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test("on the bot's turn the Reroll button is hidden", () => {
  renderScreen(rerollState(true), vi.fn(), null, vi.fn(), 1)

  expect(screen.queryByRole('button', { name: 'Reroll' })).not.toBeInTheDocument()
})

test('Reroll exposes its keyboard shortcut to assistive tech', () => {
  renderScreen(rerollState(true))

  expect(screen.getByRole('button', { name: 'Reroll' })).toHaveAttribute('aria-keyshortcuts', 'e')
})

test('pressing e rerolls when charges remain', () => {
  const sendAction = renderScreen(rerollState(true))

  fireEvent.keyDown(window, { key: 'e' })

  expect(sendAction).toHaveBeenCalledWith({ type: 'reroll' })
})

test('holding e does not reroll again on each auto-repeat', () => {
  const sendAction = renderScreen(rerollState(true))

  fireEvent.keyDown(window, { key: 'e' })
  fireEvent.keyDown(window, { key: 'e', repeat: true })
  fireEvent.keyDown(window, { key: 'e', repeat: true })

  expect(sendAction).toHaveBeenCalledTimes(1)
})

test('pressing e does nothing once charges are exhausted', () => {
  const sendAction = renderScreen(rerollState(false))

  fireEvent.keyDown(window, { key: 'e' })

  expect(sendAction).not.toHaveBeenCalled()
})

test('the Rerolls row shows each player\'s charges left against the limit', () => {
  const state = rerollState(true)
  state.game.players['1'].houseRules.reroll = { used: 1, limit: 3 }
  state.game.players['2'].houseRules.reroll = { used: 2, limit: 2 }
  renderScreen(state)

  expect(rowValues('Rerolls')).toEqual(['2 / 3', '0 / 2'])
})

test('there is no Rerolls row when the house rule is off', () => {
  renderScreen(makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } }))

  expect(within(scoreTable()).queryByRole('row', { name: /^Rerolls/ })).not.toBeInTheDocument()
})

test('with Reroll off and Comeback on the Rerolls row is there from the start and a grant only changes its number', () => {
  const comebackOnly = () => {
    const state = makeState({ turn: { recentTurns: [], currentPlayerId: 1, turnState: 'choosingPlacement', lastRoll: [3, 4], legalPlacements: [] } })
    state.game.houseRules.comebackNudge.enabled = true
    return state
  }
  const update = renderPlaying(comebackOnly())
  expect(rowValues('Rerolls')).toEqual(['0 / 0', '0 / 0'])

  const granted = comebackOnly()
  granted.game.players['1'].houseRules.reroll = { used: 0, limit: 1 }
  granted.game.players['1'].houseRules.comebackNudge.granted = true
  update(granted)

  expect(rowValues('Rerolls')).toEqual(['1 / 1', '0 / 0'])
})

test('the key hint names the reroll key, comma-joined, while placing, and is blank while skipping', () => {
  renderScreen(rerollState(true))
  expect(screen.getByText('Arrows move, N next, Enter places, R rotates, E rerolls')).toBeInTheDocument()

  cleanup()
  renderScreen(rerollState(true, 'skipped'))
  expect(document.getElementById('board-help')).toHaveTextContent(/^\s*$/)
})

test('the key hint omits the reroll key once charges are exhausted', () => {
  renderScreen(rerollState(false))

  expect(screen.getByText('Arrows move, N next, Enter places, R rotates')).toBeInTheDocument()
})

test('the turn status line offers reroll as an alternative to a forced skip', () => {
  renderScreen(rerollState(true, 'skipped'))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move — skip (S), or reroll (E)')
})

test('the turn status line skips the reroll mention once charges are exhausted', () => {
  renderScreen(rerollState(false, 'skipped'))

  expect(screen.getByTestId('turn-status')).toHaveTextContent('Player 1: no legal move, skipping… (S)')
})
