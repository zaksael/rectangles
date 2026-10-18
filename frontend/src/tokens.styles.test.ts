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

test('no screen stylesheet defines .visually-hidden again', () => {
  const sheets = readdirSync('src', { recursive: true, encoding: 'utf8' }).filter((f) => f.endsWith('.css') && f !== 'tokens.css')

  const definers = sheets.filter((f) => /^\.visually-hidden\b/m.test(readFileSync(`src/${f}`, 'utf8')))

  expect(definers).toEqual([])
})
