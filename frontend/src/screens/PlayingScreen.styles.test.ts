import { expect, test } from 'vitest'
import { contrast, danger, ledger, mix, readCss, ruleFor, token, tokensCss } from '../testUtils/styles'

const css = readCss('screens/PlayingScreen.css')

test('on touch screens the key hint is blanked by colour (also under forced colors), so its height stays reserved and the board keeps its description', () => {
  const block = css.match(/@media \(pointer: coarse\) \{\s*\.board-help \{([^}]*)\}/)![1]

  expect(block).toMatch(/color:\s*transparent/)
  expect(block).toMatch(/forced-color-adjust:\s*none/) // forced colors would otherwise paint the blanked line back in
  expect(block).not.toMatch(/display|visibility|height/)
})

test('Roll, the toolbar\'s one primary button, gets a 2px border to set it apart from Menu', () => {
  const block = ruleFor(css, '.toolbar-leading .btn.primary')

  expect(block).toMatch(/border-width:\s*2px/)
})

test('the heavier Roll border is scoped to the toolbar: primary and secondary buttons stay 1px everywhere else', () => {
  expect(ruleFor(tokensCss, '.btn.primary')).toMatch(/border:\s*1px solid/)
  expect(ruleFor(tokensCss, '.btn.secondary')).toMatch(/border:\s*1px solid/)
  expect(css).not.toMatch(/^\.btn\.primary\s*\{/m)
})

test('Reroll sits apart from the action button before it: a margin on the second button, not the shared gap', () => {
  const block = ruleFor(css, '.toolbar-leading .btn + .btn')
  const margin = Number(block.match(/margin-left:\s*(\d+)px/)![1])

  expect(margin).toBeGreaterThan(0)
})

test('the toolbar row holds the Wildcard picker height only while the Wildcard rule is on, so the frame does not grow on a wildcard roll', () => {
  const base = ruleFor(css, '.toolbar-actions')
  const reserved = ruleFor(css, '.reserves-picker .toolbar-actions')

  expect(base).toMatch(/--picker-height:\s*0px/)
  expect(reserved).toMatch(/--picker-height:\s*54px/)
  expect(base).toMatch(/grid-auto-rows:\s*minmax\(var\(--picker-height\),\s*auto\)/)
})

test('--chrome on the frame covers the header, status, hint and toolbar, and grows by the picker only while the rule is on', () => {
  const chrome = Number(ruleFor(css, '.frame').match(/--chrome:\s*(\d+)px/)![1])
  const reserved = Number(ruleFor(css, '.frame.reserves-picker').match(/--chrome:\s*(\d+)px/)![1])

  expect(chrome).toBeGreaterThanOrEqual(200)
  expect(reserved).toBeGreaterThanOrEqual(220)
})

const coarse = css.match(/@media \(any-pointer: coarse\) \{\s*\.reserves-picker \.toolbar-actions \{([^}]*)\}\s*\.wildcard-pills \.pill \{([^}]*)\}\s*\.frame\.reserves-picker \{([^}]*)\}/)

test('on any touch input (touchscreen laptops too) the Wildcard pills are 44px targets and the toolbar row reserves their taller picker', () => {
  expect(coarse).not.toBeNull()
  expect(coarse![1]).toMatch(/--picker-height:\s*92px/)
  expect(coarse![2]).toMatch(/min-width:\s*44px/)
  expect(coarse![2]).toMatch(/min-height:\s*44px/)
})

test('on touch screens --chrome grows with the taller toolbar, so the board still fits the window', () => {
  expect(Number(coarse![3].match(/--chrome:\s*(\d+)px/)![1])).toBeGreaterThanOrEqual(257)
})

test('a streak one skip from the limit is danger-coloured and bold, and stays AA (4.5:1) on the ledger and both current-player tints', () => {
  const rule = ruleFor(css, '.streak.last-skip')

  expect(rule).toMatch(/color:\s*var\(--danger\)/)
  expect(rule).toMatch(/font-weight:\s*600/)
  expect(contrast(danger, ledger)).toBeGreaterThanOrEqual(4.5)
  for (const player of ['--p1', '--p2']) {
    const tint = mix(token(tokensCss, player), 0.14, ledger)
    expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
  }
})

test('the special-cell legend is a 12px line whose marks keep their ink under forced colors', () => {
  expect(ruleFor(css, '.playing-legend')).toMatch(/font-size:\s*12px/)
  expect(ruleFor(css, '.playing-legend-mark')).toMatch(/forced-color-adjust:\s*none/) // only .board opts out, and the legend sits outside it
})

test('a frame with a legend gives the board 24px less height, whichever --chrome it has (plain, Wildcard picker, touch)', () => {
  expect(ruleFor(css, '.frame.has-legend')).toMatch(/--legend-height:\s*24px/)
  expect(ruleFor(readCss('components/Board.css'), '.board')).toMatch(/var\(--chrome, 176px\) - var\(--legend-height, 0px\)/)
})
