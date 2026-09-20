import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import { ModeSelectScreen } from './ModeSelectScreen'

beforeEach(() => {
  localStorage.clear()
})

test('on first launch, defaults to Vs Bot selected with Start Game enabled', () => {
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={vi.fn()} />)

  expect(screen.getByRole('radio', { name: 'Vs Bot' })).toHaveAttribute('aria-checked', 'true')
  expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
})

test('Start Game with default settings passes the documented first-launch connect params', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame).toHaveBeenCalledWith({
    boardSize: 19,
    skipLimit: 5,
    botSeats: 2,
    botDifficulty: 'Greedy',
    prizeEnabled: true,
    pitfallEnabled: false,
    stealEnabled: true,
    wallsEnabled: true,
    obstaclesEnabled: false,
    selfEnclosedPenaltyEnabled: true,
    wildcardEnabled: false,
    rerollEnabled: false,
    comebackNudgeEnabled: false,
  })
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

test('toggling a house rule checkbox flips it in the Start Game params', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('checkbox', { name: 'Pitfall' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame.mock.calls[0][0]).toMatchObject({ pitfallEnabled: true })
})

test('Enter activates a non-native radio/checkbox widget', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.keyDown(screen.getByRole('radio', { name: 'Local 2P' }), { key: 'Enter' })

  expect(screen.getByRole('radio', { name: 'Local 2P' })).toHaveAttribute('aria-checked', 'true')
})

test('selecting Best of 3 includes seriesLength in Start Game params', () => {
  const onStartGame = vi.fn()
  render(<ModeSelectScreen isConnecting={false} connectFailed={false} onStartGame={onStartGame} />)

  fireEvent.click(screen.getByRole('radio', { name: 'Best of 3' }))
  fireEvent.click(screen.getByRole('button', { name: 'Start Game' }))

  expect(onStartGame.mock.calls[0][0]).toMatchObject({ seriesLength: 3 })
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

  expect(screen.getByText("Couldn't connect — try again")).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Start Game' })).not.toBeDisabled()
})
