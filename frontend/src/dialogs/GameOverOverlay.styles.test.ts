import { expect, test } from 'vitest'
import { mixShare, readCss, ruleFor, textContrast, tokensCss } from '../dev/testUtils/styles'

const css = readCss('PlayingScreen.css')

test('game-over capitals are for structural labels only: the reason and table headers keep them, the swing tag, caption and player labels are normal case at 12px+', () => {
  for (const selector of ['.game-over-swing-tag', '.game-over-caption', '.game-over-scoreboard .who']) {
    const block = ruleFor(css, selector)
    expect(block, selector).not.toMatch(/text-transform/)
    expect(block, selector).not.toMatch(/letter-spacing/)
    expect(Number(block.match(/font(?:-size)?:\s*(?:\d+ )?(\d+)px/)![1]), selector).toBeGreaterThanOrEqual(12)
  }
  expect(ruleFor(tokensCss, 'dialog.modal .reason')).toMatch(/text-transform:\s*uppercase/)
  expect(ruleFor(css, '.game-over table.breakdown thead th')).toMatch(/text-transform:\s*uppercase/)
})

test('the series total under a round score is a muted 12px+ mono line', () => {
  const block = ruleFor(css, '.game-over-scoreboard .series-total')
  expect(Number(block.match(/font(?:-size)?:\s*(?:\d+ )?(\d+)px/)![1])).toBeGreaterThanOrEqual(12)
  expect(block).toMatch(/IBM Plex Mono/)
  expect(block).toMatch(/color-mix/)
})

test('the series ledger sets its total row apart: bold, ruled above, winner total larger', () => {
  const total = ruleFor(css, '.game-over table.breakdown tr.total th,\n.game-over table.breakdown tr.total td')
  expect(total).toMatch(/font-weight:\s*600/)
  expect(total).toMatch(/border-top:/)
  expect(ruleFor(css, '.game-over table.breakdown td.win')).toMatch(/font-size:\s*15px/)
})

test('a breakdown header keeps its dot and name on one line, so the dot never stacks above the name', () => {
  expect(ruleFor(css, '.game-over table.breakdown thead th')).toMatch(/white-space:\s*nowrap/)
})

test('a breakdown header keeps 16px between one player\'s name and the next player\'s dot', () => {
  expect(ruleFor(css, '.game-over table.breakdown thead th')).toMatch(/padding-left:\s*16px/)
})

test('the dice line is at least 12px and its muted ink still passes AA on the ledger', () => {
  const block = ruleFor(css, '.game-over-luck')

  expect(Number(block.match(/font-size:\s*(\d+)px/)?.[1])).toBeGreaterThanOrEqual(12)
  expect(block).toMatch(/color:\s*var\(--ink-muted\)/)
  expect(textContrast(css, '.game-over-luck')).toBeGreaterThanOrEqual(4.5)
})

test('the trailing total is 70% ink, so it clears 4.5:1 and still reads as the lower number', () => {
  const rule = ruleFor(css, '.game-over-scoreboard .trail .n')

  expect(mixShare(rule, 'color', '--ink')).toBe(0.7)
  expect(textContrast(css, '.game-over-scoreboard .trail .n')).toBeGreaterThanOrEqual(4.5)
})
