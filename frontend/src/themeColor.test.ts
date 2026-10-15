import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { tokensCss } from './dev/testUtils/styles'

// index.html cannot read a CSS variable, so its theme-color is a copy of --ledger; this keeps the two in step.
test('the theme-color in index.html is the page background, --ledger', () => {
  const html = readFileSync('index.html', 'utf8')
  const themeColor = html.match(/name="theme-color"\s+content="(#[0-9a-f]{6})"/i)?.[1]
  const ledger = tokensCss.match(/--ledger:\s*(#[0-9a-f]{6})/i)?.[1]

  expect(themeColor?.toLowerCase()).toBeDefined()
  expect(themeColor?.toLowerCase()).toBe(ledger?.toLowerCase())
})
