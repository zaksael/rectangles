import { expect, test } from 'vitest'
import { contrast, danger, ledger, mix, mixShare, readCss, ruleFor, textContrast } from '../testUtils/styles'

const css = readCss('screens/ModeSelectScreen.css')

test('the Mode Select changed-from-defaults cue keeps AA contrast (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.changed-count')).toBeGreaterThanOrEqual(4.5)
})

test('the failed-connect line is a status block: 13px bold-ish text, a danger rule and tint, and AA (4.5:1) on that tint', () => {
  const rule = ruleFor(css, '.start-error')
  const tint = mix(danger, mixShare(rule, 'background', '--danger'), ledger)

  expect(rule).toMatch(/font-size:\s*13px/)
  expect(rule).toMatch(/font-weight:\s*500/)
  expect(rule).toMatch(/border-left:\s*3px solid var\(--danger\)/)
  expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
})

test('the shared .pill (difficulty and Wildcard pills) is at least 12px, with no per-screen override', () => {
  const shared = ruleFor(css, '.pill')

  expect(Number(shared.match(/font-size:\s*(\d+)px/)![1])).toBeGreaterThanOrEqual(12)
  expect(css).not.toMatch(/\.difficulty-pills \.pill \{/)
})

test('the difficulty pills start at the left edge of their left-aligned card: the row is not centred', () => {
  const rule = ruleFor(css, '.difficulty-pills')

  expect(rule).not.toMatch(/justify-content:\s*center/)
})

test('the Mode Select title is a 24px screen title whose weight comes from .title, not an inherited override', () => {
  const rule = ruleFor(css, '.mode-select .title')

  expect(rule).toMatch(/font-size:\s*24px/)
  expect(rule).not.toMatch(/font-weight/)
})
