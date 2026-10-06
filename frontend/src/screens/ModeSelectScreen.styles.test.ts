import { expect, test } from 'vitest'
import { contrast, danger, ledger, mix, mixShare, readCss, ruleFor, textContrast } from '../testUtils/styles'

const css = readCss('screens/ModeSelectScreen.css')

test('the Mode Select changed-from-defaults cue keeps AA contrast (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.changed-count')).toBeGreaterThanOrEqual(4.5)
})

test('the failed-connect line is a status block: 13px bold-ish text, a full danger border and tint, and AA (4.5:1) on that tint', () => {
  const rule = ruleFor(css, '.start-error')
  const tint = mix(danger, mixShare(rule, 'background', '--danger'), ledger)

  expect(rule).toMatch(/font-size:\s*13px/)
  expect(rule).toMatch(/font-weight:\s*500/)
  expect(rule).toMatch(/border:\s*1px solid var\(--danger\)/)
  expect(rule).not.toMatch(/border-(left|right)/)
  expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
})

test('Start Game, the screen\'s one primary button, gets a 2px border to set it apart from the 1px options', () => {
  expect(ruleFor(css, '.mode-select .btn.primary')).toMatch(/border-width:\s*2px/)
})

test('the touch-target growth applies to any device with a touch input, so touchscreen laptops (whose primary pointer is fine) get it', () => {
  expect(css).toContain('@media (any-pointer: coarse)')
  expect(css).not.toContain('@media (pointer: coarse)')
  const block = css.match(/@media \(any-pointer: coarse\) \{([\s\S]*?)\n\}/)![1]
  for (const selector of ['.pill', '.segmented button', '.reset-link']) expect(block).toContain(`${selector} {`)
})

test('a described house rule is already taller than a 44px touch target, so it gets no extra touch padding', () => {
  const block = css.match(/@media \(any-pointer: coarse\) \{([\s\S]*?)\n\}/)![1]

  expect(block).not.toContain('.rule {')
})

test('a house rule puts its checkbox on the name line, spaces blocks 10px apart, and shows its description at 12px and AA contrast', () => {
  expect(ruleFor(css, '.rule')).toMatch(/align-items:\s*flex-start/)
  expect(ruleFor(css, '.rules-grid')).toMatch(/gap:\s*10px/)
  expect(ruleFor(css, '.rule-desc')).toMatch(/font-size:\s*12px/)
  expect(textContrast(css, '.rule-desc')).toBeGreaterThanOrEqual(4.5)
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
