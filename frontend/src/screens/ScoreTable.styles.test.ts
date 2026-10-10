import { expect, test } from 'vitest'
import { readCss, ruleFor, textContrast } from '../testUtils/styles'

const css = readCss('screens/ScoreTable.css')

test('the score table sits in a 1px card border in the line colour', () => {
  expect(css).toMatch(/\.score-table\s*\{[^}]*border:\s*1px solid var\(--line\)/)
})

test('the Total is the table\'s strongest figure', () => {
  const block = ruleFor(css, '.score-table tfoot td')

  expect(block).toMatch(/font-size:\s*20px/)
  expect(block).toMatch(/font-weight:\s*600/)
})

test('muted zeros stay AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.score-table td.zero')).toBeGreaterThanOrEqual(4.5)
})

test('a header cell never wraps, so a long name like Bot (Greedy) keeps the column', () => {
  expect(ruleFor(css, '.score-table thead th')).toMatch(/white-space:\s*nowrap/)
})
