import { expect, test } from 'vitest'
import { readCss, ruleFor, textContrast } from '../testUtils/styles'

const css = readCss('screens/ReplayScreen.css')

test('the board is fitted to the window with the rail beside it, leaving 50px of chrome', () => {
  expect(ruleFor(css, '.replay')).toMatch(/--chrome:\s*50px/)
})

test('the stepping buttons invert on hover only where there is a hover, and a disabled one does not', () => {
  const media = css.match(/@media \(hover: hover\) \{([\s\S]*?)\n\}/)![1]

  expect(media).toMatch(/\.rail \.btn:hover:not\(:disabled\)\s*\{[^}]*background:\s*var\(--ink\)/)
  expect(css.replace(media, '')).not.toMatch(/:hover/)
})

test('on Replay the piece just placed gets a 3px ink outline and a light tint, heavier than Playing\'s', () => {
  const block = ruleFor(css, '.replay .piece-outline.last')

  expect(block).toMatch(/border-width:\s*3px/)
  expect(block).toMatch(/background:\s*color-mix\(in srgb, white 30%, transparent\)/)
})

test('the Total is the table\'s strongest figure', () => {
  const block = ruleFor(css, '.replay .breakdown tfoot td')

  expect(block).toMatch(/font-size:\s*20px/)
  expect(block).toMatch(/font-weight:\s*600/)
})

test('muted zeros and the caption\'s step label stay AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .breakdown td.zero')).toBeGreaterThanOrEqual(4.5)
  expect(textContrast(css, '.replay .caption .step')).toBeGreaterThanOrEqual(4.5)
})
