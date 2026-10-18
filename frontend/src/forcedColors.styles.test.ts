import { expect, test } from 'vitest'
import { readCss, ruleFor, tokensCss } from './dev/testUtils/styles'

const css = readCss('PlayingScreen.css')

test('the board, player dots and swatches, and the game-over outcome rule keep their colours under forced colors (they are backgrounds that mode would drop)', () => {
  const board = ruleFor(readCss('Board.css'), '.board')
  const dots = ruleFor(tokensCss, '.dot,\n.swatch')
  const outcome = ruleFor(css, 'dialog.game-over::before')

  for (const rule of [board, dots, outcome]) expect(rule).toMatch(/forced-color-adjust:\s*none/)
})
