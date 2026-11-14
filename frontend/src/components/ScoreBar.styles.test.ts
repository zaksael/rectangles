import { expect, test } from 'vitest'
import { contrast, readCss, ruleFor, token, tokensCss } from '../dev/testUtils/styles'

const css = readCss('ScoreBar.css')
const white = [255, 255, 255]

test('white 20px numbers pass AA (4.5:1) on both bar segments', () => {
  expect(contrast(white, token(tokensCss, '--p1'))).toBeGreaterThanOrEqual(4.5)
  expect(contrast(white, token(css, '--bar-p2'))).toBeGreaterThanOrEqual(4.5)
})

test('the bar keeps its 36px in a short window, where the rail\'s flex column would shrink it to nothing', () => {
  const bar = ruleFor(css, '.score-bar')

  expect(bar).toMatch(/height:\s*36px/)
  expect(bar).toMatch(/flex:\s*none/)
})

test('each number is positioned above both segments, at its own end of the bar', () => {
  const num = ruleFor(css, '.score-bar-num')

  expect(num).toMatch(/position:\s*absolute/)
  expect(num).toMatch(/z-index:\s*1/)
  expect(ruleFor(css, '.score-bar-num.left')).toMatch(/left:\s*8px/)
  expect(ruleFor(css, '.score-bar-num.right')).toMatch(/right:\s*8px/)
})
