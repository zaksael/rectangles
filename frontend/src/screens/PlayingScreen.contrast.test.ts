import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'

const rgb = (hex: string) => [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16))
const token = (css: string, name: string) => rgb(css.match(new RegExp(`${name}:\\s*#([0-9a-f]{6})`, 'i'))![1])

// WCAG 2.x relative luminance and contrast ratio.
function luminance(color: number[]) {
  const [r, g, b] = color.map((v) => (v / 255 <= 0.03928 ? v / 255 / 12.92 : ((v / 255 + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const contrast = (a: number[], b: number[]) => (Math.max(luminance(a), luminance(b)) + 0.05) / (Math.min(luminance(a), luminance(b)) + 0.05)

test('disabled toolbar buttons keep their text at AA contrast (4.5:1) on the ledger', () => {
  const tokens = readFileSync('src/tokens.css', 'utf8')
  const css = readFileSync('src/screens/PlayingScreen.css', 'utf8')
  const rule = css.match(/\.toolbar-actions \.btn:disabled \{[^}]*\}/)![0]
  const share = Number(rule.match(/color:\s*color-mix\(in srgb, var\(--ink\) (\d+)%/)![1]) / 100
  const ink = token(tokens, '--ink')
  const ledger = token(tokens, '--ledger')
  const text = ink.map((v, i) => v * share + ledger[i] * (1 - share))

  expect(contrast(text, ledger)).toBeGreaterThanOrEqual(4.5)
})
