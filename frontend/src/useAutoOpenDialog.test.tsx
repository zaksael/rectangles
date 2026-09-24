import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import { useAutoOpenDialog } from './useAutoOpenDialog'

function Modal({ autoFocus = false }: { autoFocus?: boolean }) {
  const ref = useAutoOpenDialog()
  return (
    <dialog ref={ref}>
      <button autoFocus={autoFocus}>Close</button>
    </dialog>
  )
}

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
