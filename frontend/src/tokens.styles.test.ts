import { readdirSync, readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { ruleFor, tokensCss } from './dev/testUtils/styles'

test('tokens.css defines .visually-hidden: one pixel, clipped and out of the flow', () => {
  const block = ruleFor(tokensCss, '.visually-hidden')

  expect(block).toMatch(/position:\s*absolute/)
  expect(block).toMatch(/width:\s*1px/)
  expect(block).toMatch(/height:\s*1px/)
  expect(block).toMatch(/overflow:\s*hidden/)
  expect(block).toMatch(/clip-path:\s*inset\(50%\)/)
})

// Classes the screens share live in tokens.css; a screen stylesheet that defines one again would split its look in two.
test.each(['visually-hidden', 'pill', 'dot'])('no screen stylesheet defines .%s', (name) => {
  const sheets = readdirSync('src', { recursive: true, encoding: 'utf8' }).filter((f) => f.endsWith('.css') && f !== 'tokens.css')

  const definers = sheets.filter((f) => new RegExp(`^\\.${name}\\b`, 'm').test(readFileSync(`src/${f}`, 'utf8')))

  expect(definers).toEqual([])
})

test('the shared .pill (difficulty and Wildcard pills) is at least 12px', () => {
  const shared = ruleFor(tokensCss, '.pill')

  expect(Number(shared.match(/font-size:\s*(\d+)px/)![1])).toBeGreaterThanOrEqual(12)
})

test('a selected .pill fills with ink, and an unselected one tints on hover and a little more on press', () => {
  expect(ruleFor(tokensCss, '.pill.active')).toMatch(/background:\s*var\(--ink\)/)
  expect(ruleFor(tokensCss, '.pill:hover:not(.active)')).toMatch(/color-mix\(in srgb, var\(--ink\) 8%/)
  expect(ruleFor(tokensCss, '.pill:active:not(.active)')).toMatch(/color-mix\(in srgb, var\(--ink\) 16%/)
})

test('on any touch input (touchscreen laptops too) a .pill grows its hit area to 10px by 14px', () => {
  const block = tokensCss.match(/@media \(any-pointer: coarse\) \{\s*\.pill \{([^}]*)\}/)?.[1] ?? '(no .pill rule in an any-pointer: coarse block)'

  expect(block).toMatch(/padding:\s*10px 14px/)
})

test('a player .dot is 11px square and never shrinks in a flex row', () => {
  const block = ruleFor(tokensCss, '.dot')

  expect(block).toMatch(/width:\s*11px/)
  expect(block).toMatch(/height:\s*11px/)
  expect(block).toMatch(/flex:\s*none/)
})
