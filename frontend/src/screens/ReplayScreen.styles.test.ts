import { expect, test } from 'vitest'
import { contrast, ledger, mix, mixShare, readCss, ruleFor, textContrast, token, tokensCss } from '../testUtils/styles'

const css = readCss('screens/ReplayScreen.css')

test('the board is fitted to the window with the rail beside it, leaving 50px of chrome', () => {
  expect(ruleFor(css, '.replay')).toMatch(/--chrome:\s*50px/)
})

test('the stepping buttons invert on hover only where there is a hover, and a disabled one does not', () => {
  const media = css.match(/@media \(hover: hover\) \{([\s\S]*?)\n\}/)![1]

  expect(media).toMatch(/\.rail \.btn:hover:not\(:disabled\)\s*\{[^}]*background:\s*var\(--ink\)/)
  expect(css.replace(media, '')).not.toMatch(/:hover/)
})

test('on Replay the piece just placed gets a 3px ink outline and a light tint, heavier than Playing\'s', () => {
  const block = ruleFor(css, '.replay .piece-outline.last')

  expect(block).toMatch(/border-width:\s*3px/)
  expect(block).toMatch(/background:\s*color-mix\(in srgb, white 30%, transparent\)/)
})

test('the Total is the table\'s strongest figure', () => {
  const block = ruleFor(css, '.replay .breakdown tfoot td')

  expect(block).toMatch(/font-size:\s*20px/)
  expect(block).toMatch(/font-weight:\s*600/)
})

test('muted zeros and the caption\'s step label stay AA (4.5:1) on the ledger', () => {
  expect(textContrast(css, '.replay .breakdown td.zero')).toBeGreaterThanOrEqual(4.5)
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

test('chart axis numbers are 12px mono and stay AA (4.5:1) on the ledger', () => {
  const block = ruleFor(css, '.replay .chart-axis')
  const ink = token(tokensCss, '--ink')

  expect(block).toMatch(/font-size:\s*12px/)
  expect(block).toMatch(/font-family:\s*'IBM Plex Mono'/)
  expect(contrast(mix(ink, mixShare(block, 'fill', '--ink'), ledger), ledger)).toBeGreaterThanOrEqual(4.5)
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
