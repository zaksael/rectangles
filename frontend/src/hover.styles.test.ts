import { readdirSync } from 'node:fs'
import { expect, test } from 'vitest'
import { readCss } from './dev/testUtils/styles'

test('every :hover rule sits under @media (hover: hover), so a tap on a touch screen leaves no hover look behind', () => {
  const sheets = readdirSync('src', { recursive: true, encoding: 'utf8' }).filter((f) => f.endsWith('.css')).map((f) => f.split('/').pop()!)
  const unguarded = sheets.filter((name) => {
    const css = readCss(name).replace(/\/\*[\s\S]*?\*\//g, '').replace(/@media \(hover: hover\) \{[\s\S]*?\n\}/g, '')
    return css.includes(':hover')
  })

  expect(unguarded).toEqual([])
})
