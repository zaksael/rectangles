import { expect, test } from 'vitest'
import { readCss, ruleFor } from '../dev/testUtils/styles'

const css = readCss('Board.css')

test('a wall strip lets pointer events through to the cell under it', () => {
  expect(ruleFor(css, '.wall')).toMatch(/pointer-events:\s*none/)
})
