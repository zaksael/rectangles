import { expect, test } from 'vitest'
import { contrast, danger, ledger, readCss, ruleFor, tokensCss } from '../testUtils/styles'

const css = readCss('screens/PlayingScreen.css')

test('on touch screens the key hint is blanked by colour (also under forced colors), so its height stays reserved and the board keeps its description', () => {
  const block = css.match(/@media \(pointer: coarse\) \{\s*\.board-help \{([^}]*)\}/)![1]

  expect(block).toMatch(/color:\s*transparent/)
  expect(block).toMatch(/forced-color-adjust:\s*none/) // forced colors would otherwise paint the blanked line back in
  expect(block).not.toMatch(/display|visibility|height/)
})

test('Roll, the action row\'s one primary button, gets a 2px border to set it apart from the secondary buttons', () => {
  const block = ruleFor(css, '.rail-actions .btn.primary')

  expect(block).toMatch(/border-width:\s*2px/)
})

test('the heavier Roll border is scoped to the action row: primary and secondary buttons stay 1px everywhere else', () => {
  expect(ruleFor(tokensCss, '.btn.primary')).toMatch(/border:\s*1px solid/)
  expect(ruleFor(tokensCss, '.btn.secondary')).toMatch(/border:\s*1px solid/)
  expect(css).not.toMatch(/^\.btn\.primary\s*\{/m)
})

test('the action buttons sit 8px apart, Reroll included, so a shown key chip fits between them', () => {
  const block = ruleFor(css, '.rail-actions')

  expect(block).toMatch(/gap:\s*8px/)
  expect(css).not.toMatch(/\.rail-actions \.btn \+ \.btn/)
})

test('the board fits the window height less the frame\'s 52px of chrome, the same as Replay: 24px padding and 1px border, and the board\'s own border, each twice', () => {
  expect(ruleFor(css, '.playing')).toMatch(/--chrome:\s*52px/)
})

test('the rail is a 360px border-box column that scrolls by itself rather than outgrow the window', () => {
  const block = ruleFor(css, '.playing .rail')

  expect(block).toMatch(/box-sizing:\s*border-box/)
  expect(block).toMatch(/width:\s*360px/)
  expect(block).toMatch(/max-height:\s*calc\(100dvh - 2px\)/)
  expect(block).toMatch(/overflow-y:\s*auto/)
})

test('on any touch input (touchscreen laptops too) the action buttons and dice are 44px tall and the Wildcard pills are 44px targets', () => {
  const media = css.match(/@media \(any-pointer: coarse\) \{\s*\.playing \{([^}]*)\}\s*\.wildcard-pills \.pill \{([^}]*)\}/)

  expect(media).not.toBeNull()
  expect(media![1]).toMatch(/--control-height:\s*44px/)
  expect(media![2]).toMatch(/min-width:\s*44px/)
  expect(media![2]).toMatch(/min-height:\s*44px/)
})

test('a streak one skip from the limit is danger-coloured and bold, and stays AA (4.5:1) on the ledger', () => {
  const rule = ruleFor(css, '.score-table .last-skip')

  expect(rule).toMatch(/color:\s*var\(--danger\)/)
  expect(rule).toMatch(/font-weight:\s*600/)
  expect(contrast(danger, ledger)).toBeGreaterThanOrEqual(4.5)
})

test('the special-cell legend is a 12px line whose marks keep their ink under forced colors', () => {
  expect(ruleFor(css, '.playing-legend')).toMatch(/font-size:\s*12px/)
  expect(ruleFor(css, '.playing-legend-mark')).toMatch(/forced-color-adjust:\s*none/) // only .board opts out, and the legend sits outside it
})

test('the turn instruction is 14px on a 20px line at weight 500, so two lines and the hint fit the status box', () => {
  const block = ruleFor(css, '.turn-status')

  expect(block).toMatch(/font-size:\s*14px/)
  expect(block).toMatch(/line-height:\s*20px/)
  expect(block).toMatch(/font-weight:\s*500/)
})

test('the game-over buttons share the row equally but are never narrower than their label, so Series Result and Replay Last Round stay on one line', () => {
  expect(ruleFor(css, '.game-over .actions .btn')).toMatch(/min-width:\s*max-content/)
})

test('under 480px the game-over actions stack full width, since three buttons side by side wrap their labels in the narrow dialog', () => {
  const media = css.match(/@media \(max-width: 480px\) \{([\s\S]*?)\n\}/)![1]

  expect(media).toMatch(/\.game-over \.actions \{[^}]*flex-direction:\s*column/)
  expect(media).toMatch(/\.game-over \.actions \.btn \{[^}]*min-width:\s*0/)
})

test('the status line and the key hint share one 72px box that is always reserved (a two-row status over a two-row hint with Reroll on), so the controls below never move', () => {
  expect(ruleFor(css, '.rail-instr')).toMatch(/min-height:\s*72px/)
})

test('the dice slot holds the Wildcard picker height only while the Wildcard rule is on: 54px, a plain die row otherwise', () => {
  expect(ruleFor(css, '.rail-dice')).toMatch(/min-height:\s*var\(--control-height\)/)
  expect(ruleFor(css, '.rail-dice.reserves-picker')).toMatch(/min-height:\s*54px/)
})

test('the action row is a fixed 58px even when no button applies, and the notice row a fixed 46px (two toast rows), toasts starting at its top', () => {
  expect(ruleFor(css, '.rail-actions')).toMatch(/height:\s*58px/)
  expect(ruleFor(css, '.rail-notice')).toMatch(/min-height:\s*46px/)
  expect(ruleFor(css, '.rail-notice')).toMatch(/justify-content:\s*flex-start/)
})

test('on touch the dice slot holds 92px and the action row 66px, in a block after the base rules so the cascade lets them win', () => {
  const touch = css.match(/@media \(any-pointer: coarse\) \{\s*\.rail-dice\.reserves-picker \{([^}]*)\}\s*\.rail-actions \{([^}]*)\}/)

  expect(touch![1]).toMatch(/min-height:\s*92px/)
  expect(touch![2]).toMatch(/height:\s*66px/)
  expect(touch!.index).toBeGreaterThan(css.indexOf('\n.rail-dice.reserves-picker {'))
  expect(touch!.index).toBeGreaterThan(css.indexOf('\n.rail-actions {'))
})

test('the key hint is pinned to the bottom of the status box, so a one-row and a two-row status leave it in the same place', () => {
  expect(ruleFor(css, '.rail-instr .board-help')).toMatch(/margin-top:\s*auto/)
})

test('the Moves rows use 2px of vertical padding, so four of them and the rest of the rail fit a 888px frame', () => {
  expect(ruleFor(css, '.move')).toMatch(/padding:\s*2px 0/)
})

test('on touch the Moves list gives up its fourth row, which the taller buttons need', () => {
  expect(css).toMatch(/@media \(any-pointer: coarse\) \{[^@]*\.history \.move:nth-child\(n \+ 4\) \{[^}]*display:\s*none/)
})

test('a header dot is a ring only while its player is neither the mover nor over: at game over both are filled', () => {
  expect(css).toMatch(/\.score-table thead th:not\(\.current\):not\(\.over\) \.dot \{[^}]*background:\s*transparent/)
})

test('the Moves list is a size container that can shrink to two rows (26px heading + 2 x 43px rows = 112px) before the rail scrolls', () => {
  const block = ruleFor(css, '.rail-history')

  expect(block).toMatch(/container-type:\s*size/)
  expect(block).toMatch(/min-height:\s*112px/)
})

test('a short Moves list sheds its fourth row under 197px and its third under 155px, the heights four and three rows need', () => {
  expect(css).toMatch(/@container \(max-height: 196px\) \{\s*\.history \.move:nth-child\(n \+ 4\) \{[^}]*display:\s*none/)
  expect(css).toMatch(/@container \(max-height: 154px\) \{\s*\.history \.move:nth-child\(n \+ 3\) \{[^}]*display:\s*none/)
})
