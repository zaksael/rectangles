import { expect, test } from 'vitest'
import { contrast, danger, ledger, mixShare, mix, readCss, ruleFor, textContrast, tokensCss } from '../testUtils/styles'

const css = readCss('screens/PlayingScreen.css')

test('off house-rule labels in the Menu keep AA contrast (4.5:1) on the ledger, dimmer than on rules', () => {
  expect(textContrast(css, '.settings-rule')).toBeGreaterThanOrEqual(4.5)
  expect(css).toMatch(/\.settings-rule\.on \{[^}]*color: var\(--ink\)/)
})

test('the Menu note explaining the unavailable Surrender keeps AA contrast (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.settings-footer-note')).toBeGreaterThanOrEqual(4.5)
})

test('the quiet Surrender is an outline, a transparent fill with a danger-coloured label that keeps AA contrast (4.5:1) on the ledger', () => {
  const rule = ruleFor(tokensCss, '.btn.destructive.quiet')

  expect(rule).toMatch(/background:\s*transparent/)
  expect(rule).toMatch(/color:\s*var\(--danger\)/)
  expect(contrast(danger, ledger)).toBeGreaterThanOrEqual(4.5)
})

test('the quiet Surrender hovers to a light danger tint, not the solid button\'s black-mixed darkening, with its label still AA', () => {
  const rule = ruleFor(tokensCss, '.btn.destructive.quiet:hover')
  const tint = mix(danger, mixShare(rule, 'background', '--danger'), ledger)

  expect(rule).not.toMatch(/black/)
  expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
})

test('an unavailable but focusable quiet Surrender is dimmed by colour, not opacity, so its focus ring stays full ink, and shows no hover tint', () => {
  const selector = '.btn.destructive.quiet[aria-disabled="true"]'
  const rule = ruleFor(tokensCss, selector)

  expect(rule).toMatch(/color:\s*color-mix\(/)
  expect(rule).toMatch(/background:\s*transparent/)
  expect(rule).not.toMatch(/opacity/)
  // Same specificity as the hover rule, so it must come later to win while hovered.
  expect(tokensCss.indexOf(selector)).toBeGreaterThan(tokensCss.indexOf('.btn.destructive.quiet:hover'))
})

test('the Menu header holds a lone title, so it declares no flex layout or gap for it', () => {
  const rule = ruleFor(css, '.settings-header')

  expect(rule).not.toMatch(/display|align-items|gap/)
})
