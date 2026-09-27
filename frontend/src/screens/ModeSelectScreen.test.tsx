import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { ModeSelectScreen } from './ModeSelectScreen'

beforeEach(() => {
  localStorage.clear()
})

test('the screen title is a heading', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('heading', { name: 'New Game' })).toBeInTheDocument()
})

test('on first launch, no mode is selected and Start Game is disabled with a hint', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('radio', { name: 'Vs Bot' })).toHaveAttribute('aria-checked', 'false')
  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'false')
  const startButton = screen.getByRole('button', { name: 'Start Game' })
  expect(startButton).toBeDisabled()
  expect(startButton).toHaveAccessibleDescription('Choose a mode to configure the match')
})

test('selecting a mode enables Start Game and clears the hint', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
  expect(screen.queryByText('Choose a mode to configure the match')).not.toBeInTheDocument()
})

test('Start Game with default settings passes the documented first-launch connect params, with no house-rule flags', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame).toHaveBeenCalledWith({
    boardSize: 19,
    skipLimit: 5,
    botSeats: 2,
    botDifficulty: 'Greedy',
  })
})

test('no house rules are shown until their UI is implemented', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(screen.queryAllByRole('checkbox')).toHaveLength(0)
  expect(screen.queryByText('House rules')).not.toBeInTheDocument()
})

test('selecting Local 2P hides the difficulty pills and omits botSeats/botDifficulty from Start Game', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))
  expect(screen.queryByRole('radio', { name: 'Greedy' })).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame).toHaveBeenCalledWith(expect.not.objectContaining({ botSeats: expect.anything() }))
  expect(onStartGame.mock.calls[0][0]).not.toHaveProperty('botDifficulty')
})

test('the difficulty-pills row stays mounted (reserving its space) even when it is hidden', () => {
  const { container } = render(
    <ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />,
  )

  expect(container.querySelector('.difficulty-pills')).toBeInTheDocument()

  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))
  expect(container.querySelector('.difficulty-pills')).toBeInTheDocument()
  expect(container.querySelector('.difficulty-pills')).toHaveClass('hidden')

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  expect(container.querySelector('.difficulty-pills')).not.toHaveClass('hidden')
})

test('hidden difficulty pills are inert (unreachable by keyboard, not just visually hidden)', () => {
  const { container } = render(
    <ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />,
  )

  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))

  const pillsContainer = container.querySelector('.difficulty-pills') as HTMLDivElement
  expect(pillsContainer).toHaveAttribute('inert')

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  expect(pillsContainer).not.toHaveAttribute('inert')
})

test('Enter activates a non-native radio/checkbox widget', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.keyDown(screen.getByRole('radio', { name: 'Local 2P' }), { key: 'Enter' })

  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'true')
})

// Series play needs the round-transition screen, so the Games picker stays hidden until it lands.
test('hides the Games picker while series play is not implemented', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(screen.getByRole('radiogroup', { name: 'Skip limit' })).toBeInTheDocument()
  expect(screen.queryByRole('radiogroup', { name: 'Games' })).not.toBeInTheDocument()
  expect(screen.queryByRole('radio', { name: 'Best of 3' })).not.toBeInTheDocument()
})

test('does not send seriesLength even when a stored setting has one', () => {
  localStorage.setItem('rectangles.modeSelectSettings:v1', JSON.stringify({ seriesLength: 3 }))
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame.mock.calls[0][0]).not.toHaveProperty('seriesLength')
})

test('persists settings to localStorage on Start Game and pre-fills them on the next mount', () => {
  const { unmount } = render(
    <ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />,
  )
  fireEvent.click(screen.getByRole('radio', { name: 'Local 2P' }))
  fireEvent.click(screen.getByRole('radio', { name: '23×23' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))
  unmount()

  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('radio', { name: '23×23' })).toHaveAttribute('aria-checked', 'true')
})

test('while isConnecting, Start Game is disabled and reads Connecting…', () => {
  render(<ModeSelectScreen isConnecting connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('button', { name: 'Connecting…' })).toBeDisabled()
})

test('while connectFailed, shows an inline retry message and Start Game stays enabled', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed onStartGame={vi.fn()} />)
  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))

  expect(
    screen.getByText('Couldn’t connect — your settings are unchanged, try again'),
  ).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
})

test('Reset to defaults opens a confirm dialog', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('button', { name: 'Reset to defaults' }))

  expect(screen.getByRole('heading', { name: 'Reset to defaults?' })).toBeInTheDocument()
})

test('confirming the reset dialog restores match setup but keeps the chosen opponent', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('radio', { name: '23×23' }))
  fireEvent.click(screen.getByRole('radio', { name: 'Blocking' }))

  fireEvent.click(screen.getByRole('button', { name: 'Reset to defaults' }))
  fireEvent.click(screen.getByRole('button', { name: 'Reset' }))

  expect(screen.queryByRole('heading', { name: 'Reset to defaults?' })).not.toBeInTheDocument()
  expect(screen.getByRole('radio', { name: 'Vs Bot' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('radio', { name: '19×19' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('radio', { name: 'Greedy' })).toHaveAttribute('aria-checked', 'true')
})

test('cancelling the reset dialog leaves settings untouched', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Vs Bot' }))
  fireEvent.click(screen.getByRole('radio', { name: '23×23' }))

  fireEvent.click(screen.getByRole('button', { name: 'Reset to defaults' }))
  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

  expect(screen.queryByRole('heading', { name: 'Reset to defaults?' })).not.toBeInTheDocument()
  expect(screen.getByRole('radio', { name: '23×23' })).toHaveAttribute('aria-checked', 'true')
})
