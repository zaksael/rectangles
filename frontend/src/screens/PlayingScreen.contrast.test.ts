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

// Contrast of a rule's `color-mix(in srgb, var(--ink) N%, transparent)` text on the ledger.
function textContrast(css: string, selector: RegExp) {
  const tokens = readFileSync('src/tokens.css', 'utf8')
  const share = Number(css.match(new RegExp(`${selector.source} \\{[^}]*color:\\s*color-mix\\(in srgb, var\\(--ink\\) (\\d+)%`))![1]) / 100
  const ink = token(tokens, '--ink')
  const ledger = token(tokens, '--ledger')
  return contrast(ink.map((v, i) => v * share + ledger[i] * (1 - share)), ledger)
}

const css = readFileSync('src/screens/PlayingScreen.css', 'utf8')

test('off house-rule labels in the Menu keep AA contrast (4.5:1) on the ledger, dimmer than on rules', () => {
  expect(textContrast(css, /\.settings-rule/)).toBeGreaterThanOrEqual(4.5)
  expect(css).toMatch(/\.settings-rule\.on \{[^}]*color: var\(--ink\)/)
})

test('the Menu note explaining the unavailable Surrender keeps AA contrast (4.5:1) on the ledger', () => {
  expect(textContrast(css, /\.settings-footer-note/)).toBeGreaterThanOrEqual(4.5)
})

const tokensCss = readFileSync('src/tokens.css', 'utf8')
const ruleFor = (selector: string) => {
  const i = tokensCss.indexOf(selector)
  return tokensCss.slice(tokensCss.indexOf('{', i), tokensCss.indexOf('}', i))
}
const danger = token(tokensCss, '--danger')
const ledgerRgb = token(tokensCss, '--ledger')

test('the quiet Surrender is an outline, a transparent fill with a danger-coloured label that keeps AA contrast (4.5:1) on the ledger', () => {
  const rule = ruleFor('.btn.destructive.quiet')

  expect(rule).toMatch(/background:\s*transparent/)
  expect(rule).toMatch(/color:\s*var\(--danger\)/)
  expect(contrast(danger, ledgerRgb)).toBeGreaterThanOrEqual(4.5)
})

test('the quiet Surrender hovers to a light danger tint, not the solid button\'s black-mixed darkening, with its label still AA', () => {
  const rule = ruleFor('.btn.destructive.quiet:hover')
  const share = Number(rule.match(/background:\s*color-mix\(in srgb, var\(--danger\) (\d+)%, transparent\)/)![1]) / 100
  const tint = danger.map((v, i) => v * share + ledgerRgb[i] * (1 - share))

  expect(rule).not.toMatch(/black/)
  expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
})

test('an unavailable but focusable quiet Surrender is dimmed by colour, not opacity, so its focus ring stays full ink, and shows no hover tint', () => {
  const selector = '.btn.destructive.quiet[aria-disabled="true"]'
  const rule = ruleFor(selector)

  expect(rule).toMatch(/color:\s*color-mix\(/)
  expect(rule).toMatch(/background:\s*transparent/)
  expect(rule).not.toMatch(/opacity/)
  // Same specificity as the hover rule, so it must come later to win while hovered.
  expect(tokensCss.indexOf(selector)).toBeGreaterThan(tokensCss.indexOf('.btn.destructive.quiet:hover'))
})

test('the Mode Select changed-from-defaults cue keeps AA contrast (4.5:1) on the ledger', () => {
  const modeSelectCss = readFileSync('src/screens/ModeSelectScreen.css', 'utf8')
  expect(textContrast(modeSelectCss, /\.changed-count/)).toBeGreaterThanOrEqual(4.5)
})

test('on touch screens the key hint is blanked by colour, so its height stays reserved and the board keeps its description', () => {
  const block = css.match(/@media \(pointer: coarse\) \{\s*\.board-help \{([^}]*)\}/)![1]

  expect(block).toMatch(/color:\s*transparent/)
  expect(block).not.toMatch(/display|visibility|height/)
})

test('Reroll sits apart from the action button before it: a margin on the second button, not the shared gap', () => {
  const block = css.match(/\.toolbar-leading \.btn \+ \.btn \{([^}]*)\}/)![1]
  const margin = Number(block.match(/margin-left:\s*(\d+)px/)![1])

  expect(margin).toBeGreaterThan(0)
})

test('the toolbar row always reserves the Wildcard picker height, so the frame does not grow on a wildcard roll', () => {
  const toolbar = css.match(/\.toolbar-actions \{([^}]*)\}/)![1]

  expect(toolbar).toMatch(/--picker-height:\s*54px/)
  expect(toolbar).toMatch(/grid-auto-rows:\s*minmax\(var\(--picker-height\),\s*auto\)/)
})

test('--chrome on the frame is at least what the header, status, hint and the reserved toolbar need', () => {
  const chrome = Number(css.match(/\.frame \{[^}]*--chrome:\s*(\d+)px/)![1])

  expect(chrome).toBeGreaterThanOrEqual(220)
})

const coarse = css.match(/@media \(pointer: coarse\) \{\s*\.toolbar-actions \{([^}]*)\}\s*\.wildcard-pills \.pill \{([^}]*)\}\s*\.frame \{([^}]*)\}/)

test('on touch screens the Wildcard pills are 44px targets and the toolbar row reserves their taller picker', () => {
  expect(coarse).not.toBeNull()
  expect(coarse![1]).toMatch(/--picker-height:\s*92px/)
  expect(coarse![2]).toMatch(/min-width:\s*44px/)
  expect(coarse![2]).toMatch(/min-height:\s*44px/)
})

test('on touch screens --chrome grows with the taller toolbar, so the board still fits the window', () => {
  expect(Number(coarse![3].match(/--chrome:\s*(\d+)px/)![1])).toBeGreaterThanOrEqual(257)
})

test('a streak one skip from the limit is danger-coloured and bold, and stays AA (4.5:1) on the ledger and both current-player tints', () => {
  const rule = css.match(/\.streak\.last-skip \{([^}]*)\}/)![1]

  expect(rule).toMatch(/color:\s*var\(--danger\)/)
  expect(rule).toMatch(/font-weight:\s*600/)
  expect(contrast(danger, ledgerRgb)).toBeGreaterThanOrEqual(4.5)
  for (const player of ['--p1', '--p2']) {
    const p = token(tokensCss, player)
    const tint = p.map((v, i) => v * 0.14 + ledgerRgb[i] * 0.86)
    expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
  }
})

test('the Menu header holds a lone title, so it declares no flex layout or gap for it', () => {
  const rule = css.match(/\.settings-header \{([^}]*)\}/)![1]

  expect(rule).not.toMatch(/display|align-items|gap/)
})

test('the failed-connect line is a status block: 13px bold-ish text, a danger rule and tint, and AA (4.5:1) on that tint', () => {
  const rule = readFileSync('src/screens/ModeSelectScreen.css', 'utf8').match(/\.start-error \{([^}]*)\}/)![1]
  const share = Number(rule.match(/background:\s*color-mix\(in srgb, var\(--danger\) (\d+)%, transparent\)/)![1]) / 100
  const tint = danger.map((v, i) => v * share + ledgerRgb[i] * (1 - share))

  expect(rule).toMatch(/font-size:\s*13px/)
  expect(rule).toMatch(/font-weight:\s*500/)
  expect(rule).toMatch(/border-left:\s*3px solid var\(--danger\)/)
  expect(contrast(danger, tint)).toBeGreaterThanOrEqual(4.5)
})

test('game-over capitals are for structural labels only: the reason and table headers keep them, the swing tag, caption and player labels are normal case at 12px+', () => {
  const rule = (selector: string) => css.match(new RegExp(`${selector.replace(/[.\s]/g, (c) => `\\${c}`)} \\{([^}]*)\\}`))![1]

  for (const selector of ['.game-over-swing-tag', '.game-over-caption', '.game-over-scoreboard .who']) {
    const block = rule(selector)
    expect(block, selector).not.toMatch(/text-transform/)
    expect(block, selector).not.toMatch(/letter-spacing/)
    expect(Number(block.match(/font(?:-size)?:\s*(?:\d+ )?(\d+)px/)![1]), selector).toBeGreaterThanOrEqual(12)
  }
  expect(rule('dialog.modal .reason')).toMatch(/text-transform:\s*uppercase/)
  expect(rule('.game-over table.breakdown thead th')).toMatch(/text-transform:\s*uppercase/)
})

test('the shared .pill (difficulty and Wildcard pills) is at least 12px, with no per-screen override', () => {
  const modeSelectCss = readFileSync('src/screens/ModeSelectScreen.css', 'utf8')
  const shared = modeSelectCss.match(/\n\.pill \{([^}]*)\}/)![1]

  expect(Number(shared.match(/font-size:\s*(\d+)px/)![1])).toBeGreaterThanOrEqual(12)
  expect(modeSelectCss).not.toMatch(/\.difficulty-pills \.pill \{/)
})

test('the difficulty pills start at the left edge of their left-aligned card: the row is not centred', () => {
  const rule = readFileSync('src/screens/ModeSelectScreen.css', 'utf8').match(/\n\.difficulty-pills \{([^}]*)\}/)![1]

  expect(rule).not.toMatch(/justify-content:\s*center/)
})

test('the Mode Select title is a 24px screen title whose weight comes from .title, not an inherited override', () => {
  const rule = readFileSync('src/screens/ModeSelectScreen.css', 'utf8').match(/\.mode-select \.title \{([^}]*)\}/)![1]

  expect(rule).toMatch(/font-size:\s*24px/)
  expect(rule).not.toMatch(/font-weight/)
})
