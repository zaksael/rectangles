import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

afterEach(cleanup)

// The screens are laid out for a desktop window; jsdom's default 1024px would show the narrow-window notice.
// Restored after every test, so one that fails while narrowed the window doesn't leak the width into the next.
const DESKTOP_WIDTH = 1400
const setDesktopWidth = () => Object.defineProperty(window, 'innerWidth', { configurable: true, value: DESKTOP_WIDTH })
setDesktopWidth()
afterEach(setDesktopWidth)

// jsdom doesn't implement <dialog>'s showModal()/close() yet.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.setAttribute('open', '')
    // The dialog focusing steps: a browser focuses the first focusable element once the dialog is open (React's autoFocus runs while it is still closed, where nothing can take focus).
    this.querySelector<HTMLElement>('button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')?.focus()
  }
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    this.removeAttribute('open')
  }
}
