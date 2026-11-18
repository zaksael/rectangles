import { expect, test } from 'vitest'
import { contrast, ledger, mix, mixShare, readCss, ruleFor, textContrast, token, tokensCss } from '../dev/testUtils/styles'

const css = readCss('ReplayScreen.css')

test('the board is fitted to the window with the rail beside it, leaving 52px of chrome: the frame\'s 24px padding and 1px border, and the board\'s own 1px border, each twice', () => {
  expect(ruleFor(css, '.replay')).toMatch(/--chrome:\s*52px/)
})

test('the round and the series score stack, one above the other', () => {
  expect(ruleFor(css, '.replay .rail-series')).toMatch(/flex-direction:\s*column/)
})

test('only the stepping buttons invert on hover, only where there is a hover, and a disabled one does not', () => {
  const media = css.match(/@media \(hover: hover\) \{([\s\S]*?)\n\}/)![1]!

  expect(media).toMatch(/\.replay \.transport \.btn:hover:not\(:disabled\):not\(\[aria-disabled="true"\]\)\s*\{[^}]*background:\s*var\(--ink\)/)
  expect(media).not.toMatch(/\.replay \.rail \.btn:hover/)
  expect(css.replace(media, '')).not.toMatch(/:hover/)
})

test('an unavailable stepping button is dimmed by colour, not opacity, so its focus ring stays full ink, and has no hover tint', () => {
  const rule = ruleFor(css, '.replay .transport .btn[aria-disabled="true"]')

  expect(rule).toMatch(/color:\s*color-mix\(in srgb, var\(--ink\)/)
  expect(rule).toMatch(/border-color:\s*currentcolor/)
  expect(rule).toMatch(/background:\s*transparent/)
  expect(rule).toMatch(/cursor:\s*default/)
  expect(rule).not.toMatch(/opacity/)
})

test('on Replay the piece just placed gets a 3px ink outline and a light tint, heavier than Playing\'s', () => {
  const block = ruleFor(css, '.replay .piece-outline.last')

  expect(block).toMatch(/border-width:\s*3px/)
  expect(block).toMatch(/background:\s*color-mix\(in srgb, white 30%, transparent\)/)
})

test('the caption\'s step label stays AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .caption .step')).toBeGreaterThanOrEqual(4.5)
})

test('the flagged-turn row buttons are dimmed when unavailable and invert on hover like the transport', () => {
  expect(css).toMatch(/\.replay \.flag-nav \.btn\[aria-disabled="true"\]\s*\{[^}]*cursor:\s*default/)
  expect(css.match(/@media \(hover: hover\) \{([\s\S]*?)\n\}/)![1]).toMatch(/\.replay \.flag-nav \.btn:hover:not\(:disabled\):not\(\[aria-disabled="true"\]\)/)
})

test('the transport has five columns with a wider middle one for Play, and the speed row three buttons centred under the middle three', () => {
  expect(css).toMatch(/\.replay \.transport,\s*\.replay \.speed \{[^}]*grid-template-columns:\s*1fr 1fr 1\.6fr 1fr 1fr/)
  expect(ruleFor(css, '.replay .speed .btn:first-child')).toMatch(/grid-column:\s*2/)
})

test('Play is bold but not filled, since filled means playing, pressed or hovered', () => {
  expect(css).toMatch(/\.replay \.transport \.play\s*\{[^}]*font-weight:\s*600/)
  expect(css).not.toMatch(/\.replay \.transport \.play\s*\{[^}]*background/)
})

test('Pause and the chosen speed are shown inverted, in ink on the ledger', () => {
  for (const selector of ['.replay .play.replay-playing', ".replay .speed .btn[aria-pressed='true']"]) {
    const block = ruleFor(css, selector)
    expect(block).toMatch(/background:\s*var\(--ink\)/)
    expect(block).toMatch(/color:\s*var\(--ledger\)/)
  }
})

test('nothing on Replay animates, so autoplay has no motion to reduce', () => {
  expect(css).not.toMatch(/transition|animation|@keyframes/)
})

test('the chart is 300px tall but is the one thing that gives up height, down to 112px', () => {
  const block = ruleFor(css, '.replay .chart-body')

  expect(block).toMatch(/flex:\s*1 1 300px/)
  expect(block).toMatch(/min-height:\s*112px/)
  expect(block).toMatch(/max-height:\s*300px/)
  expect(block).toMatch(/overflow:\s*hidden/) // so the drawing never props the box open
})

test('the chart wrapper has no box, so the chart shrinks to its 112px floor instead of spilling over the controls', () => {
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

test('the caption keeps room for the label, two lines of move and the result line, so the last step does not resize the chart', () => {
  const block = ruleFor(css, '.replay .caption')
  const step = ruleFor(css, '.replay .caption .step')
  const verdict = ruleFor(css, '.replay .caption .verdict')

  expect(block).toMatch(/line-height:\s*18px/)
  expect(step).toMatch(/line-height:\s*13px/)
  expect(step).toMatch(/margin-bottom:\s*4px/)
  expect(verdict).toMatch(/display:\s*block/)
  expect(verdict).toMatch(/margin-top:\s*4px/)
  expect(verdict).toMatch(/font-weight:\s*600/)
  expect(verdict).toMatch(/color:\s*var\(--ink\)/)
  expect(block).toMatch(/min-height:\s*75px/) // the label's 13px + 4px, 2 lines of 18px, then the result's 4px + 18px
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

test('the readout is 12px mono beside the label, and the hint is 12px and AA (4.5:1), free to share a row with the chart key', () => {
  const readout = ruleFor(css, '.replay .chart-readout')
  const hint = ruleFor(css, '.replay .chart-hint')

  expect(readout).toMatch(/font-family:\s*'IBM Plex Mono'/)
  expect(readout).toMatch(/font-size:\s*12px/)
  expect(readout).toMatch(/margin-left:\s*auto/)
  expect(hint).toMatch(/font-size:\s*12px/)
  expect(hint).not.toMatch(/flex-basis/)
  expect(textContrast(css, '.replay .chart-hint')).toBeGreaterThanOrEqual(4.5)
})

// --- turn analysis ---

const boardCss = readCss('Board.css')

test('the note slot reserves a two-line note so a note coming and going never resizes the chart', () => {
  expect(ruleFor(css, '.replay .analysis-slot')).toMatch(/min-height:\s*44px/)
})

test('the muted note lines and the chart key stay AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .analysis.pending')).toBeGreaterThanOrEqual(4.5)
  expect(textContrast(css, '.replay .chart-key')).toBeGreaterThanOrEqual(4.5)
})

test('a flagged note has a full-ink rule on its left and a muted one has a hairline', () => {
  expect(ruleFor(css, '.replay .analysis')).toMatch(/border-left:\s*2px solid var\(--ink\)/)
  expect(ruleFor(css, '.replay .analysis.pending')).toMatch(/border-left-color:\s*var\(--line\)/)
})

test('the count that leads a flagged note is muted and ends with a period', () => {
  expect(ruleFor(css, '.replay .analysis-lead')).toMatch(/color:\s*var\(--ink-muted\)/)
  expect(ruleFor(css, '.replay .analysis-lead::after')).toMatch(/content:\s*'\.'/)
})

test('the pressed Show Better Option toggle is inverted, in ink on the ledger', () => {
  const block = ruleFor(css, ".replay .flag-nav .btn[aria-pressed='true']:not([aria-disabled='true'])")

  expect(block).toMatch(/background:\s*var\(--ink\)/)
  expect(block).toMatch(/color:\s*var\(--ledger\)/)
})

test('the flagged row has the toggle between two equal buttons, and no label wraps', () => {
  expect(ruleFor(css, '.replay .flag-nav')).toMatch(/grid-template-columns:\s*1fr auto 1fr/)
  expect(ruleFor(css, '.replay .flag-nav .btn')).toMatch(/white-space:\s*nowrap/)
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
  expect(ruleFor(css, '.replay .controls-hint')).toMatch(/color:\s*var\(--ink-muted\)/)
  expect(css).toMatch(/@media \(pointer: coarse\) \{\s*\.replay \.controls-hint \{[^}]*display:\s*none/)
})

test('the Replay rail buttons are 30px tall: 5px of padding above and below, in the head, transport, speed and flag rows alike', () => {
  for (const selector of ['.replay .rail .btn', '.replay .transport .btn', '.replay .speed .btn', '.replay .flag-nav .btn']) {
    expect(ruleFor(css, selector)).toMatch(/padding:\s*5px (0|8px|16px)/)
  }
})

test('any touch input keeps the playback buttons at their old 36px height', () => {
  expect(css).toMatch(/@media \(any-pointer: coarse\) \{[^@]*\.replay \.controls \.btn \{[^}]*min-height:\s*36px/)
})

test('the Replay score table packs its rows tighter than the shared one: 3px body rows, a 7px head, a 6px Total and a 3px In reach row', () => {
  expect(ruleFor(css, '.replay .score-table td')).toMatch(/padding:\s*3px 8px/)
  expect(ruleFor(css, '.replay .score-table thead th')).toMatch(/padding:\s*7px 8px/)
  expect(ruleFor(css, '.replay .score-table tfoot td')).toMatch(/padding:\s*6px 8px/)
  expect(ruleFor(css, '.replay .score-table tfoot .res-first td')).toMatch(/padding:\s*3px 8px/)
  expect(ruleFor(css, '.replay .score-table .note-row td')).toMatch(/padding:\s*0 8px 4px/)
})

test('the Replay rail packs its blocks with an 8px gap and 16px padding; the rest comes from the shared .rail', () => {
  expect(ruleFor(css, '.replay .rail').replace(/\s+/g, ' ').trim()).toBe('gap: 8px; padding: 16px;')
})

test('the chart head sits 6px above the chart, so the chart pulls up by the rail gap less 6px', () => {
  expect(ruleFor(css, '.replay .chart-body')).toMatch(/margin-top:\s*-2px/)
})
