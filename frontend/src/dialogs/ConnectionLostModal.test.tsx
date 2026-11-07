import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { ConnectionLostModal } from './ConnectionLostModal'

test('a single game says only the game cannot be rejoined', () => {
  render(<ConnectionLostModal isSeries={false} onNewGame={vi.fn()} />)
  expect(screen.getByText(/couldn't be restored/)).not.toHaveTextContent(/series/)
})

test('an out-of-date page offers only Reload Page, which reloads and does not start a new game', () => {
  const onReload = vi.fn()
  const onNewGame = vi.fn()
  render(<ConnectionLostModal isSeries={false} onNewGame={onNewGame} outOfDate onReload={onReload} />)
  fireEvent.click(screen.getByRole('button', { name: 'Reload Page' }))
  expect(onReload).toHaveBeenCalledTimes(1)
  expect(onNewGame).not.toHaveBeenCalled()
})

test('a hidden placeholder backdrop stands behind the modal, since the last board may be stale', () => {
  const { container } = render(<ConnectionLostModal isSeries={false} onNewGame={vi.fn()} />)
  const backdrop = container.querySelector('.connection-lost-backdrop')
  expect(backdrop).toBeInTheDocument()
  expect(backdrop).toHaveAttribute('aria-hidden', 'true')
})

test('a series says the series cannot be resumed either', () => {
  render(<ConnectionLostModal isSeries onNewGame={vi.fn()} />)
  expect(screen.getByText(/couldn't be restored/)).toHaveTextContent("the series can't be resumed either")
})
