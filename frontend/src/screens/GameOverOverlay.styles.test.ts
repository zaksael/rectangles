import { expect, test } from 'vitest'
import { readCss, ruleFor } from '../testUtils/styles'

const css = readCss('screens/PlayingScreen.css')

test('game-over capitals are for structural labels only: the reason and table headers keep them, the swing tag, caption and player labels are normal case at 12px+', () => {
  for (const selector of ['.game-over-swing-tag', '.game-over-caption', '.game-over-scoreboard .who']) {
    const block = ruleFor(css, selector)
    expect(block, selector).not.toMatch(/text-transform/)
    expect(block, selector).not.toMatch(/letter-spacing/)
    expect(Number(block.match(/font(?:-size)?:\s*(?:\d+ )?(\d+)px/)![1]), selector).toBeGreaterThanOrEqual(12)
  }
  expect(ruleFor(css, 'dialog.modal .reason')).toMatch(/text-transform:\s*uppercase/)
  expect(ruleFor(css, '.game-over table.breakdown thead th')).toMatch(/text-transform:\s*uppercase/)
})

test('the series total under a round score is a muted 12px+ mono line', () => {
  const block = ruleFor(css, '.game-over-scoreboard .series-total')
  expect(Number(block.match(/font(?:-size)?:\s*(?:\d+ )?(\d+)px/)![1])).toBeGreaterThanOrEqual(12)
  expect(block).toMatch(/IBM Plex Mono/)
  expect(block).toMatch(/color-mix/)
})
