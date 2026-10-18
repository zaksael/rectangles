import { readdirSync, readFileSync } from 'node:fs'

// Helpers for tests that assert on stylesheet text (jsdom has no layout, so the rules themselves are the seam).
// Looked up by file name anywhere under src/, so moving a stylesheet between folders breaks no test.
export const readCss = (name: string) => {
  const found = readdirSync('src', { recursive: true, encoding: 'utf8' }).filter((f) => f.split('/').pop() === name)
  if (found.length !== 1) throw new Error(`readCss: expected one ${name} under src/, found ${found.length}`)
  return readFileSync(`src/${found[0]}`, 'utf8')
}

const rgb = (hex: string) => [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16))
export const token = (css: string, name: string) => rgb(css.match(new RegExp(`${name}:\\s*#([0-9a-f]{6})`, 'i'))![1]!)

export const tokensCss = readCss('tokens.css')
export const danger = token(tokensCss, '--danger')
export const ledger = token(tokensCss, '--ledger')

// WCAG 2.x relative luminance and contrast ratio.
function luminance(color: number[]) {
  const [r, g, b] = color.map((v) => (v / 255 <= 0.03928 ? v / 255 / 12.92 : ((v / 255 + 0.055) / 1.055) ** 2.4)) as [number, number, number]
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
export const contrast = (a: number[], b: number[]) => (Math.max(luminance(a), luminance(b)) + 0.05) / (Math.min(luminance(a), luminance(b)) + 0.05)

// `fg` at `share` (0-1) over `bg`, as `color-mix(in srgb, fg N%, transparent)` renders on an opaque background.
export const mix = (fg: number[], share: number, bg: number[]) => fg.map((v, i) => v * share + bg[i]! * (1 - share))

export const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

// The body of the rule whose selector starts a line, e.g. ruleFor(css, '.start-error'); else the first rule whose comma list contains it.
export function ruleFor(css: string, selector: string) {
  const own = css.match(new RegExp(`(?:^|\\n)${escape(selector)} \\{([^}]*)\\}`))
  const listed = css.match(new RegExp(`(?:^|\\n)(?:[^{}]*,\\s*)?${escape(selector)}(?:\\s*,[^{}]*)?\\s*\\{([^}]*)\\}`))
  const match = own ?? listed
  if (!match) throw new Error(`no rule for ${selector}`)
  return match[1]!
}

// The N in a rule's `property: color-mix(in srgb, var(--token) N%, transparent)`, as a share (0-1).
export const mixShare = (rule: string, property: string, tokenName: string) =>
  Number(rule.match(new RegExp(`${property}:\\s*color-mix\\(in srgb, var\\(${tokenName}\\) (\\d+)%`))![1]!) / 100

// Contrast of a rule's `color-mix(in srgb, var(--ink) N%, transparent)` text on the ledger.
export function textContrast(css: string, selector: string) {
  const ink = token(tokensCss, '--ink')
  return contrast(mix(ink, mixShare(ruleFor(css, selector), 'color', '--ink'), ledger), ledger)
}
