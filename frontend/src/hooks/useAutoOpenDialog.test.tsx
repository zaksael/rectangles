import { fireEvent, render, screen } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { useAutoOpenDialog } from './useAutoOpenDialog'

function Modal({ autoFocus = false, onCancel }: { autoFocus?: boolean; onCancel?: () => void }) {
  const ref = useAutoOpenDialog()
  return (
    <dialog ref={ref} onCancel={onCancel}>
      <button autoFocus={autoFocus}>Close</button>
    </dialog>
  )
}

// jsdom has no layout, so every box is 0x0 at the origin: a point left of it is on the scrim.
const outsideTheBox = { clientX: -1, clientY: -1 }

function openerButton() {
  const opener = document.createElement('button')
  document.body.append(opener)
  opener.focus()
  return opener
}

test('returns focus to the element that had it before the dialog opened, once the dialog closes', () => {
  const opener = openerButton()
  const { unmount } = render(<Modal />)
  screen.getByRole('button', { name: 'Close', hidden: true }).focus() // the dialog takes focus while open
  expect(document.activeElement).not.toBe(opener)

  unmount()

  expect(document.activeElement).toBe(opener)
  opener.remove()
})

test('a press and click on the dialog itself (its scrim) cancels it through its own onCancel', () => {
  const onCancel = vi.fn()
  render(<Modal onCancel={onCancel} />)
  const dialog = screen.getByRole('dialog', { hidden: true })

  fireEvent.pointerDown(dialog, outsideTheBox)
  fireEvent.click(dialog, outsideTheBox)

  expect(onCancel).toHaveBeenCalledOnce()
})

test('a press inside the dialog released on the scrim does not cancel it', () => {
  const onCancel = vi.fn()
  render(<Modal onCancel={onCancel} />)
  const dialog = screen.getByRole('dialog', { hidden: true })

  fireEvent.pointerDown(screen.getByRole('button', { name: 'Close', hidden: true }))
  fireEvent.click(dialog)

  expect(onCancel).not.toHaveBeenCalled()
})

test('a click on the dialog padding, inside its box, does not cancel it', () => {
  const onCancel = vi.fn()
  render(<Modal onCancel={onCancel} />)
  const dialog = screen.getByRole('dialog', { hidden: true })
  dialog.getBoundingClientRect = () => new DOMRect(100, 100, 200, 100)

  fireEvent.pointerDown(dialog, { clientX: 105, clientY: 105 })
  fireEvent.click(dialog, { clientX: 105, clientY: 105 })

  expect(onCancel).not.toHaveBeenCalled()
})

test('a click on the dialog content does not cancel it', () => {
  const onCancel = vi.fn()
  render(<Modal onCancel={onCancel} />)
  const close = screen.getByRole('button', { name: 'Close', hidden: true })

  fireEvent.pointerDown(close)
  fireEvent.click(close)

  expect(onCancel).not.toHaveBeenCalled()
})

test('leaves focus alone when something else took it as the dialog closed', () => {
  const opener = openerButton()
  const { rerender } = render(
    <>
      <Modal />
      <button>Next</button>
    </>,
  )
  screen.getByRole('button', { name: 'Next' }).focus() // what an autofocused replacement does as the dialog goes

  rerender(
    <>
      {null}
      <button>Next</button>
    </>,
  )

  expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Next' }))
  opener.remove()
})

test('does nothing when the opener has since left the page', () => {
  const opener = openerButton()
  const { unmount } = render(<Modal />)
  opener.remove()

  unmount()

  expect(document.activeElement).toBe(document.body)
})

test('remembers the opener even when the dialog focuses a button as it mounts', () => {
  const opener = openerButton()
  const { unmount } = render(<Modal autoFocus />)
  expect(document.activeElement).not.toBe(opener)

  unmount()

  expect(document.activeElement).toBe(opener)
  opener.remove()
})
