import { expect, test } from 'vitest'
import { readCss, ruleFor, tokensCss } from './dev/testUtils/styles'

const css = readCss('PlayingScreen.css')

test('the board, player dots and swatches, the score bar, the game-over outcome rule and the Replay score chart keep their colours under forced colors (backgrounds that mode would drop, and lines it would recolour)', () => {
  const board = ruleFor(readCss('Board.css'), '.board')
  const dots = ruleFor(tokensCss, '.dot,\n.swatch')
  const bar = ruleFor(readCss('ScoreBar.css'), '.score-bar')
  const outcome = ruleFor(css, 'dialog.game-over::before')
  const chart = ruleFor(readCss('ReplayScreen.css'), '.replay .chart')

  for (const rule of [board, dots, bar, outcome, chart]) expect(rule).toMatch(/forced-color-adjust:\s*none/)
})

// A selected control is a background fill, which forced colors replaces with Canvas, so it must name system colours there.
function forcedColorsBlock(sheet: string) {
  const start = sheet.indexOf('@media (forced-colors: active)')
  if (start < 0) return ''
  let depth = 0
  for (let i = sheet.indexOf('{', start); i < sheet.length; i++) {
    if (sheet[i] === '{') depth++
    if (sheet[i] === '}' && --depth === 0) return sheet.slice(start, i + 1)
  }
  return ''
}

test.each([
  ['tokens.css', '.pill.active'],
  ['ModeSelectScreen.css', '.mode-segmented button.active'],
  ['ReplayScreen.css', ".replay .speed .btn[aria-pressed='true']"],
  ['ReplayScreen.css', ".replay .flag-nav .btn[aria-pressed='true']:not([aria-disabled='true'])"],
])('%s: a selected %s is filled with Highlight under forced colors', (file, selector) => {
  const block = forcedColorsBlock(readCss(file))
  const rule = block.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^{}]*\\{([^}]*)\\}`))

  expect(rule?.[1] ?? '').toMatch(/background:\s*Highlight/)
  expect(rule?.[1] ?? '').toMatch(/color:\s*HighlightText/)
})

// Dimming by a colour mix is dropped in this mode, so a focusable-but-unavailable button would look like an available one.
test.each([
  ['ReplayScreen.css', '.replay .transport .btn[aria-disabled="true"]'],
  ['ReplayScreen.css', '.replay .flag-nav .btn[aria-disabled="true"]'],
  ['tokens.css', '.btn.destructive.quiet[aria-disabled="true"]'],
])('%s: an unavailable %s reads as disabled (GrayText) under forced colors', (file, selector) => {
  const block = forcedColorsBlock(readCss(file))
  const rule = block.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^{}]*\\{([^}]*)\\}`))

  expect(rule?.[1] ?? '').toMatch(/color:\s*GrayText/)
  expect(rule?.[1] ?? '').toMatch(/border-color:\s*GrayText/)
})

test('the score chart sits on the ledger colour under forced colors, so its dark ink stays readable on a dark theme', () => {
  const block = forcedColorsBlock(readCss('ReplayScreen.css'))
  const rule = block.match(/\.replay \.chart\s*\{([^}]*)\}/)

  expect(rule?.[1] ?? '').toMatch(/background:\s*var\(--ledger\)/)
})

test('a switched-on rule checkbox keeps a visible mark under forced colors', () => {
  const block = forcedColorsBlock(readCss('ModeSelectScreen.css'))

  expect(block).toMatch(/\.mode-rule\.on \.mode-checkbox::after[^{}]*\{[^}]*background:\s*CanvasText/)
})
