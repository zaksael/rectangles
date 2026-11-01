import { render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { ConnectionLostModal } from './ConnectionLostModal'

test('a single game says only the game cannot be rejoined', () => {
  render(<ConnectionLostModal isSeries={false} onNewGame={vi.fn()} />)
  expect(screen.getByText(/couldn't be restored/)).not.toHaveTextContent(/series/)
})

test('a series says the series cannot be resumed either', () => {
  render(<ConnectionLostModal isSeries onNewGame={vi.fn()} />)
  expect(screen.getByText(/couldn't be restored/)).toHaveTextContent("the series can't be resumed either")
})
