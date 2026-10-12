import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { ConnectionLostModal } from './ConnectionLostModal'
import { ResetConfirmDialog } from './ResetConfirmDialog'
import { SurrenderConfirmDialog } from './SurrenderConfirmDialog'

function pressEscape() {
  const cancel = new Event('cancel', { cancelable: true })
  fireEvent(screen.getByRole('dialog'), cancel)
  return cancel
}

test('Escape on the reset dialog cancels it without the native close', () => {
  const onCancel = vi.fn()
  render(<ResetConfirmDialog onCancel={onCancel} onConfirm={vi.fn()} />)
  expect(pressEscape().defaultPrevented).toBe(true)
  expect(onCancel).toHaveBeenCalledOnce()
})

test('Escape on the surrender dialog cancels it without the native close', () => {
  const onCancel = vi.fn()
  render(
    <SurrenderConfirmDialog opponentName="Bot" scores={[]} isSeries={false} onCancel={onCancel} onConfirm={vi.fn()} />,
  )
  expect(pressEscape().defaultPrevented).toBe(true)
  expect(onCancel).toHaveBeenCalledOnce()
})

test('Escape does not dismiss the connection-lost modal', () => {
  const onNewGame = vi.fn()
  render(<ConnectionLostModal isSeries={false} onNewGame={onNewGame} />)
  expect(pressEscape().defaultPrevented).toBe(true)
  expect(onNewGame).not.toHaveBeenCalled()
})
