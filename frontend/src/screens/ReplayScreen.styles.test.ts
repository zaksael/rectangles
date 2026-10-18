import { expect, test } from 'vitest'
import { contrast, ledger, mix, mixShare, readCss, ruleFor, textContrast, token, tokensCss } from '../dev/testUtils/styles'

const css = readCss('ReplayScreen.css')

test('the board is fitted to the window with the rail beside it, leaving 52px of chrome: the frame\'s 24px padding and 1px border, and the board\'s own 1px border, each twice', () => {
  expect(ruleFor(css, '.replay')).toMatch(/--chrome:\s*52px/)
})

test('the round and the series score stack, one above the other', () => {
  expect(ruleFor(css, '.replay .rail-series')).toMatch(/flex-direction:\s*column/)
})

test('the stepping buttons invert on hover only where there is a hover, and a disabled one does not', () => {
  const media = css.match(/@media \(hover: hover\) \{([\s\S]*?)\n\}/)![1]!

  expect(media).toMatch(/\.replay \.rail \.btn:hover:not\(:disabled\)\s*\{[^}]*background:\s*var\(--ink\)/)
  expect(css.replace(media, '')).not.toMatch(/:hover/)
})

test('on Replay the piece just placed gets a 3px ink outline and a light tint, heavier than Playing\'s', () => {
  const block = ruleFor(css, '.replay .piece-outline.last')

  expect(block).toMatch(/border-width:\s*3px/)
  expect(block).toMatch(/background:\s*color-mix\(in srgb, white 30%, transparent\)/)
})

test('the caption\'s step label stays AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .caption .step')).toBeGreaterThanOrEqual(4.5)
})

test('the transport has five columns and the speed row three buttons centred under the middle three', () => {
  expect(css).toMatch(/\.replay \.transport,\s*\.replay \.speed \{[^}]*grid-template-columns:\s*repeat\(5, 1fr\)/)
  expect(ruleFor(css, '.replay .speed .btn:first-child')).toMatch(/grid-column:\s*2/)
})

test('Pause and the chosen speed are shown inverted, in ink on the ledger', () => {
  for (const selector of ['.replay .play.playing', ".replay .speed .btn[aria-pressed='true']"]) {
    const block = ruleFor(css, selector)
    expect(block).toMatch(/background:\s*var\(--ink\)/)
    expect(block).toMatch(/color:\s*var\(--ledger\)/)
  }
})

test('nothing on Replay animates, so autoplay has no motion to reduce', () => {
  expect(css).not.toMatch(/transition|animation|@keyframes/)
})

test('the rail never outgrows the window: it stops at the window height and scrolls by itself beyond that', () => {
  const block = ruleFor(css, '.replay .rail')

  expect(block).toMatch(/max-height:\s*calc\(100dvh - 2px\)/)
  expect(block).toMatch(/overflow-y:\s*auto/)
})

test('the chart is 300px tall but is the one thing that gives up height, down to 160px', () => {
  const block = ruleFor(css, '.replay .chart-body')

  expect(block).toMatch(/flex:\s*1 1 300px/)
  expect(block).toMatch(/min-height:\s*160px/)
  expect(block).toMatch(/max-height:\s*300px/)
  expect(block).toMatch(/overflow:\s*hidden/) // so the drawing never props the box open
})

test('the chart wrapper has no box, so the chart shrinks to its 160px floor instead of spilling over the controls', () => {
  const block = ruleFor(css, '.replay .chart-wrap')

  expect(block).toMatch(/display:\s*contents/)
})

test('chart axis numbers are 12px mono and stay AA (4.5:1) on the ledger', () => {
  const block = ruleFor(css, '.replay .chart-axis')
  const ink = token(tokensCss, '--ink')

  expect(block).toMatch(/font-size:\s*12px/)
  expect(block).toMatch(/font-family:\s*'IBM Plex Mono'/)
  expect(contrast(mix(ink, mixShare(block, 'fill', '--ink'), ledger), ledger)).toBeGreaterThanOrEqual(4.5)
})

test('the connection notice text stays AA (4.5:1) on the ledger and is outlined in the same danger colour', () => {
  const block = ruleFor(css, '.replay .conn-notice')

  expect(block).toMatch(/color:\s*var\(--danger\)/)
  expect(block).toMatch(/border:\s*1px solid var\(--danger\)/)
  expect(contrast(token(tokensCss, '--danger'), ledger)).toBeGreaterThanOrEqual(4.5)
})

test('the chart label and the empty-chart text stay AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .chart-label')).toBeGreaterThanOrEqual(4.5)
  expect(textContrast(css, '.replay .chart-empty')).toBeGreaterThanOrEqual(4.5)
})

test('the rail is 360px wide in all, padding included, so the chart gets a 320px box', () => {
  const block = ruleFor(css, '.replay .rail')

  expect(block).toMatch(/box-sizing:\s*border-box/)
  expect(block).toMatch(/width:\s*360px/)
})

test('the caption keeps room for three lines of text, so a longer or shorter caption does not resize the chart', () => {
  const block = ruleFor(css, '.replay .caption')
  const step = ruleFor(css, '.replay .caption .step')

  expect(block).toMatch(/line-height:\s*18px/)
  expect(step).toMatch(/line-height:\s*13px/)
  expect(step).toMatch(/margin-bottom:\s*4px/)
  expect(block).toMatch(/min-height:\s*71px/) // the step label's 13px + 4px, then 3 lines of 18px
})

test('the player dots in the table header and the readout carry their player colour', () => {
  expect(ruleFor(css, '.replay .dot.p1')).toMatch(/background:\s*var\(--p1\)/)
  expect(ruleFor(css, '.replay .dot.p2')).toMatch(/background:\s*var\(--p2\)/)
})

test('a jump target is invisible until hovered (where there is a hover) or keyboard-focused', () => {
  const target = ruleFor(css, '.replay .chart-hit')
  const media = css.match(/@media \(hover: hover\) \{([\s\S]*?)\n\}/)![1]
  const focus = ruleFor(css, '.replay .chart-hit:focus-visible')

  expect(target).toMatch(/fill:\s*transparent/)
  expect(target).toMatch(/cursor:\s*pointer/)
  expect(media).toMatch(/\.replay \.chart-hit:hover\s*\{[^}]*fill:\s*color-mix\(in srgb, var\(--ink\) 6%, transparent\)/)
  expect(focus).toMatch(/fill:\s*color-mix\(in srgb, var\(--ink\) 6%, transparent\)/)
  expect(focus).toMatch(/stroke:\s*var\(--ink\)/)
  expect(focus).toMatch(/stroke-width:\s*2px/)
  expect(focus).toMatch(/outline:\s*none/) // the stroke is the focus ring
})

test('lines, dots and the marker let the pointer through to the jump targets under them', () => {
  expect(css).toMatch(/\.replay \.chart-line,\s*\.replay \.chart-dot,\s*\.replay \.chart-marker \{[^}]*pointer-events:\s*none/)
})

test('the readout is 12px mono beside the label, and the hint is 12px and AA (4.5:1) on its own row', () => {
  const readout = ruleFor(css, '.replay .chart-readout')
  const hint = ruleFor(css, '.replay .chart-hint')

  expect(readout).toMatch(/font-family:\s*'IBM Plex Mono'/)
  expect(readout).toMatch(/font-size:\s*12px/)
  expect(readout).toMatch(/margin-left:\s*auto/)
  expect(hint).toMatch(/font-size:\s*12px/)
  expect(hint).toMatch(/flex-basis:\s*100%/)
  expect(textContrast(css, '.replay .chart-hint')).toBeGreaterThanOrEqual(4.5)
})

// --- turn analysis ---

const boardCss = readCss('Board.css')

test('the note slot reserves a stacked note (text, then the toggle on its own row) so a note coming and going never resizes the chart', () => {
  expect(ruleFor(css, '.replay .analysis-slot')).toMatch(/min-height:\s*56px/)
})

test('the muted note lines and the chart key stay AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .analysis.pending')).toBeGreaterThanOrEqual(4.5)
  expect(textContrast(css, '.replay .chart-key')).toBeGreaterThanOrEqual(4.5)
})

test('a flagged note has a full-ink rule on its left and a muted one has a hairline', () => {
  expect(ruleFor(css, '.replay .analysis')).toMatch(/border-left:\s*2px solid var\(--ink\)/)
  expect(ruleFor(css, '.replay .analysis.pending')).toMatch(/border-left-color:\s*var\(--line\)/)
})

test('the pressed Show Better Option toggle is inverted, in ink on the ledger', () => {
  const block = ruleFor(css, ".replay .analysis-row .btn[aria-pressed='true']")

  expect(block).toMatch(/background:\s*var\(--ink\)/)
  expect(block).toMatch(/color:\s*var\(--ledger\)/)
})

test('a long note stacks the toggle under it, and the toggle never wraps its label', () => {
  expect(ruleFor(css, '.replay .analysis-row.stacked')).toMatch(/flex-direction:\s*column/)
  expect(ruleFor(css, '.replay .analysis-row .btn')).toMatch(/white-space:\s*nowrap/)
})

test('the better placement is a 3px dashed ink outline with a light ink tint, above the pieces', () => {
  const block = ruleFor(boardCss, '.better-option')

  expect(block).toMatch(/border:\s*3px dashed var\(--ink\)/)
  expect(block).toMatch(/background:\s*color-mix\(in srgb, var\(--ink\) 12%, transparent\)/)
  expect(block).toMatch(/z-index:\s*2/)
})

test('the Better move tag is a 12px ink label on the outline\'s top-left corner, below it on the first row and from the right corner in the right half', () => {
  const tag = ruleFor(boardCss, '.better-option .tag')
  expect(tag).toMatch(/background:\s*var\(--ink\)/)
  expect(tag).toMatch(/color:\s*var\(--ledger\)/)
  expect(tag).toMatch(/font-size:\s*12px/)
  expect(tag).toMatch(/bottom:\s*100%/)
  expect(tag).toMatch(/left:\s*-3px/)
  expect(ruleFor(boardCss, '.better-option.flip .tag')).toMatch(/top:\s*100%/)
  expect(ruleFor(boardCss, '.better-option.end .tag')).toMatch(/right:\s*-3px/)
  expect(contrast(ledger, token(tokensCss, '--ink'))).toBeGreaterThanOrEqual(4.5)
})

test('the key hint is muted like the chart hint, and a touch screen, which has no keyboard, does not show it', () => {
  expect(ruleFor(css, '.replay .controls-hint')).toMatch(/color:\s*color-mix\(in srgb, var\(--ink\) 75%, transparent\)/)
  expect(css).toMatch(/@media \(pointer: coarse\) \{\s*\.replay \.controls-hint \{[^}]*display:\s*none/)
})
