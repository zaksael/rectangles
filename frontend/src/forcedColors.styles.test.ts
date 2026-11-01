import { expect, test } from 'vitest'
import { readCss, ruleFor, tokensCss } from './dev/testUtils/styles'

const css = readCss('PlayingScreen.css')

test('the board, player dots and swatches, and the game-over outcome rule keep their colours under forced colors (they are backgrounds that mode would drop)', () => {
  const board = ruleFor(readCss('Board.css'), '.board')
  const dots = ruleFor(tokensCss, '.dot,\n.swatch')
  const outcome = ruleFor(css, 'dialog.game-over::before')

  for (const rule of [board, dots, outcome]) expect(rule).toMatch(/forced-color-adjust:\s*none/)
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
  ['ModeSelectScreen.css', '.segmented button.active'],
  ['PlayingScreen.css', ".speed-options .btn[aria-pressed='true']"],
  ['ReplayScreen.css', ".replay .speed .btn[aria-pressed='true']"],
  ['ReplayScreen.css', ".replay .analysis-row .btn[aria-pressed='true']"],
])('%s: a selected %s is filled with Highlight under forced colors', (file, selector) => {
  const block = forcedColorsBlock(readCss(file))
  const rule = block.match(new RegExp(`${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[^{}]*\\{([^}]*)\\}`))

  expect(rule?.[1] ?? '').toMatch(/background:\s*Highlight/)
  expect(rule?.[1] ?? '').toMatch(/color:\s*HighlightText/)
})

test('a switched-on rule checkbox keeps a visible mark under forced colors', () => {
  const block = forcedColorsBlock(readCss('ModeSelectScreen.css'))

  expect(block).toMatch(/\.rule\.on \.checkbox::after[^{}]*\{[^}]*background:\s*CanvasText/)
})
