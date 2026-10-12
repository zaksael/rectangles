import { expect, test } from 'vitest'
import { ruleFor, tokensCss } from './dev/testUtils/styles'

test('the key chip is hidden at rest and shown while Shift is held, without taking room from the button', () => {
  const chip = ruleFor(tokensCss, '.key-badge')

  expect(chip).toMatch(/visibility:\s*hidden/)
  expect(chip).toMatch(/position:\s*absolute/) // overlaid on the corner, so nothing reflows
  expect(ruleFor(tokensCss, '[data-shift] .key-badge')).toMatch(/visibility:\s*visible/)
  expect(ruleFor(tokensCss, '.btn')).toMatch(/position:\s*relative/) // the chip's anchor
})

test('the key chip is 12px mono, and never shown on a device whose primary input is touch', () => {
  expect(ruleFor(tokensCss, '.key-badge')).toMatch(/font:[^;]*12px[^;]*'IBM Plex Mono'/)
  expect(tokensCss).toMatch(/@media \(pointer: coarse\) \{\s*\.key-badge \{\s*display:\s*none/)
})
