import { expect, test } from 'vitest'
import { readCss, ruleFor, textContrast } from '../testUtils/styles'

const css = readCss('ScoreTable.css')

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

test('a resource row (In reach) is set apart by a line-colour hairline and is plain 13px even under the Total footer', () => {
  expect(ruleFor(css, '.score-table .res-first td')).toMatch(/border-top:\s*1px solid var\(--line\)/)

  const inFooter = ruleFor(css, '.score-table tfoot .res-first td')
  expect(inFooter).toMatch(/font-size:\s*13px/)
  expect(inFooter).toMatch(/font-weight:\s*400/)
  expect(inFooter).toMatch(/padding:\s*5px 12px/)
})

test('the resource row\'s hairline lives with the shared table, not in Playing\'s own sheet', () => {
  expect(readCss('PlayingScreen.css')).not.toContain('.res-first')
})
