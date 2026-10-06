import { fireEvent, render } from '@testing-library/react'
import { afterEach, expect, test } from 'vitest'
import { useShiftHeld } from './useShiftHeld'

function Probe() {
  useShiftHeld()
  return null
}

const root = document.documentElement

afterEach(() => root.removeAttribute('data-shift'))

test('holding Shift sets data-shift on the root and releasing it clears it', () => {
  render(<Probe />)

  fireEvent.keyDown(window, { key: 'Shift' })
  expect(root).toHaveAttribute('data-shift')

  fireEvent.keyUp(window, { key: 'Shift' })
  expect(root).not.toHaveAttribute('data-shift')
})

test('losing window focus clears it, so a Shift held across an alt-tab cannot leave the badges stuck on', () => {
  render(<Probe />)
  fireEvent.keyDown(window, { key: 'Shift' })

  fireEvent.blur(window)

  expect(root).not.toHaveAttribute('data-shift')
})

test('other keys leave it alone, and unmounting stops listening and clears it', () => {
  const { unmount } = render(<Probe />)
  fireEvent.keyDown(window, { key: 'a' })
  expect(root).not.toHaveAttribute('data-shift')

  fireEvent.keyDown(window, { key: 'Shift' })
  unmount()
  expect(root).not.toHaveAttribute('data-shift')
  fireEvent.keyDown(window, { key: 'Shift' })
  expect(root).not.toHaveAttribute('data-shift')
})
