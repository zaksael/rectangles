import { expect, test } from 'vitest'
import { readCss, ruleFor, textContrast } from '../dev/testUtils/styles'

const css = readCss('NarrowWindowGate.css')

test('the notice fills the window and centres its text', () => {
  const block = ruleFor(css, '.narrow-notice')

  expect(block).toMatch(/min-height:\s*100dvh/)
  expect(block).toMatch(/align-items:\s*center/)
  expect(block).toMatch(/justify-content:\s*center/)
})

test('the notice\'s muted text stays AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.narrow-notice-reason')).toBeGreaterThanOrEqual(4.5)
  expect(textContrast(css, '.narrow-notice-text')).toBeGreaterThanOrEqual(4.5)
})
