import { expect, test } from 'vitest'
import { contrast, danger, ledger, mix, mixShare, readCss, ruleFor, textContrast } from '../dev/testUtils/styles'

const css = readCss('ModeSelectScreen.css')

test('the Mode Select changed-from-defaults cue keeps AA contrast (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.mode-changed-count')).toBeGreaterThanOrEqual(4.5)
})

test('secondary text uses the one muted-ink token, not its own ink mix', () => {
  for (const selector of ['.mode-card .mode-desc', '.mode-reset-confirm p', '.mode-field-hint', '.mode-empty-hint']) {
    expect(ruleFor(css, selector), selector).toMatch(/color:\s*var\(--ink-muted\)/)
  }
})

test('a switched-on rule shows a tick in an 18px box, drawn as a ledger-coloured corner rather than a filled square', () => {
  const mark = css.match(/\n\.mode-rule\.on \.mode-checkbox::after \{([^}]*)\}/)![1] // at line start: the forced-colors copy is indented

  expect(ruleFor(css, '.mode-checkbox')).toMatch(/width:\s*18px/)
  expect(ruleFor(css, '.mode-checkbox')).toMatch(/height:\s*18px/)
  expect(mark).toMatch(/border:\s*solid var\(--ledger\)/)
  expect(mark).not.toMatch(/background:\s*var\(--ledger\)/)
})

test('a switched-off rule reads as off at a glance: a dashed muted box and muted text', () => {
  const off = css.match(/\n\.mode-rule:not\(\.on\) \{([^}]*)\}/)?.[1] ?? ''
  const box = css.match(/\n\.mode-rule:not\(\.on\) \.mode-checkbox \{([^}]*)\}/)?.[1] ?? ''

  expect(off).toMatch(/color:\s*var\(--ink-muted\)/)
  expect(box).toMatch(/border-style:\s*dashed/)
  expect(box).toMatch(/border-color:\s*var\(--ink-muted\)/)
})

test('the failed-connect line is a status block: 13px bold-ish text, a full danger border and tint, and AA (4.5:1) on that tint', () => {
  const rule = ruleFor(css, '.mode-start-error')
  const tint = mix(danger, mixShare(rule, 'background', '--danger'), ledger)

  expect(rule).toMatch(/font-size:\s*13px/)
  expect(rule).toMatch(/font-weight:\s*500/)
  expect(rule).toMatch(/border:\s*1px solid var\(--danger\)/)
  expect(rule).not.toMatch(/border-(left|right)/)
  expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
})

test('the section labels sit one level above the group and field labels: 13px, 600, full ink against their 11px muted', () => {
  const section = ruleFor(css, '.mode-section-label')

  expect(section).toMatch(/font-size:\s*13px/)
  expect(section).toMatch(/font-weight:\s*600/)
  expect(section).toMatch(/color:\s*var\(--ink\)/)
  expect(ruleFor(css, '.mode-group-label')).toMatch(/font-size:\s*11px/)
  expect(ruleFor(css, '.mode-field-label')).toMatch(/font-size:\s*11px/)
})

test('the Match setup fields sit on the same three columns and gap as the house-rule groups, never narrower than their control', () => {
  const row = ruleFor(css, '.mode-field-row')
  const groups = ruleFor(css, '.mode-rules-groups')

  expect(row).toMatch(/display:\s*grid/)
  expect(row).toMatch(/grid-template-columns:\s*repeat\(3, minmax\(min-content, 1fr\)\)/)
  expect(row.match(/gap:\s*([^;]+);/)![1]).toBe(groups.match(/gap:\s*([^;]+);/)![1])
})

test('Match setup fields after the first are inset like the rule groups after the first, so their edges meet the rule text', () => {
  expect(ruleFor(css, '.mode-field:not(:first-child)')).toMatch(/padding-left:\s*16px/)
  expect(ruleFor(css, '.mode-rules-group')).toMatch(/padding-left:\s*16px/)
})

test('the Cancel link is centred under Start Game, like the button above it', () => {
  expect(ruleFor(css, '.mode-cancel')).toMatch(/align-self:\s*center/)
})

test('Start Game, the screen\'s one primary button, gets a 2px border to set it apart from the 1px options', () => {
  expect(ruleFor(css, '.mode-select .btn.primary')).toMatch(/border-width:\s*2px/)
})

test('the touch-target growth applies to any device with a touch input, so touchscreen laptops (whose primary pointer is fine) get it', () => {
  expect(css).toContain('@media (any-pointer: coarse)')
  expect(css).not.toContain('@media (pointer: coarse)')
  const block = css.match(/@media \(any-pointer: coarse\) \{([\s\S]*?)\n\}/)![1]
  for (const selector of ['.mode-segmented button', '.mode-group-link']) expect(block).toContain(`${selector} {`)
  expect(block).toContain('.mode-reset-link,')
  expect(block).not.toContain('.pill {') // the shared pill grows in tokens.css
})

test('a described house rule is already taller than a 44px touch target, so it gets no extra touch padding', () => {
  const block = css.match(/@media \(any-pointer: coarse\) \{([\s\S]*?)\n\}/)![1]

  expect(block).not.toContain('.mode-rule {')
})

test('a house rule puts its checkbox on the name line, spaces blocks 10px apart, and shows its description at 12px and AA contrast', () => {
  expect(ruleFor(css, '.mode-rule')).toMatch(/align-items:\s*flex-start/)
  expect(ruleFor(css, '.mode-rules-grid')).toMatch(/gap:\s*10px/)
  expect(ruleFor(css, '.mode-rule-desc')).toMatch(/font-size:\s*12px/)
  expect(textContrast(css, '.mode-rule-desc')).toBeGreaterThanOrEqual(4.5)
})

test('the difficulty pills take the shared .pill look with no per-screen override', () => {
  expect(css).not.toMatch(/\.mode-difficulty-pills \.pill \{/)
})

test('the difficulty pills start at the left edge of their left-aligned card: the row is not centred', () => {
  const rule = ruleFor(css, '.mode-difficulty-pills')

  expect(rule).not.toMatch(/justify-content:\s*center/)
})

test('the Mode Select title is a 24px screen title whose weight comes from .title, not an inherited override', () => {
  const rule = ruleFor(css, '.mode-select .title')

  expect(rule).toMatch(/font-size:\s*24px/)
  expect(rule).not.toMatch(/font-weight/)
})

// Every stylesheet is global, so a screen's own class must carry its prefix; these are shared (tokens.css) or states.
const SHARED_OR_STATE = ['active', 'btn', 'connecting', 'hidden', 'on', 'primary', 'selected', 'title']

test("Mode Select's own classes all carry the mode- prefix", () => {
  const selectors = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\{[^}]*\}/g, '{}')
  const classes = new Set([...selectors.matchAll(/\.([a-zA-Z][\w-]*)/g)].map((match) => match[1]!))
  expect([...classes].filter((name) => !name.startsWith('mode-') && !SHARED_OR_STATE.includes(name))).toEqual([])
})

test('the group header wraps so the links drop under a label in a narrow column', () => {
  expect(css).toMatch(/\.mode-group-head \{[^}]*flex-wrap:\s*wrap/)
})

test('the group links share the Reset link\u2019s style and its coarse-pointer padding', () => {
  expect(css).toMatch(/\.mode-reset-link,\s*\.mode-group-link \{/)
  expect(css).toMatch(/@media \(any-pointer: coarse\) \{[\s\S]*\.mode-reset-link,\s*\.mode-group-link \{[^}]*padding:\s*12px 0/)
})

test('the difficulty strength pips take the pill’s own colour, filled up to the tier, and stay visible in forced colours', () => {
  expect(ruleFor(css, '.mode-pill-scale')).toMatch(/display:\s*inline-flex/)
  expect(ruleFor(css, '.mode-pill-scale i')).toMatch(/border:\s*1px solid currentColor/)
  expect(ruleFor(css, '.mode-pill-scale i.on')).toMatch(/background:\s*currentColor/)
  expect(ruleFor(css, '.mode-pill-scale i')).toMatch(/forced-color-adjust:\s*none/)
})

test('the Reset dialog’s width and text styles live in Mode Select’s sheet, not Playing’s', () => {
  expect(css).toMatch(/dialog\.mode-reset-confirm \{[^}]*width:\s*400px/)
  expect(readCss('PlayingScreen.css')).not.toContain('reset-confirm')
})
