import { expect, test } from 'vitest'
import { scoreShare } from './scoreShare'

test('two positive scores split the bar by their share of the total', () => {
  expect(scoreShare(12, 8)).toBe(60)
})

test('0 against 0 splits the bar evenly', () => {
  expect(scoreShare(0, 0)).toBe(50)
})

test('a negative score gets none of the bar and the other player all of it', () => {
  expect(scoreShare(8, -3)).toBe(100)
  expect(scoreShare(-3, 8)).toBe(0)
})

test('with both scores at or below zero the smaller loss gets the larger share', () => {
  expect(scoreShare(-4, -1)).toBe(20)
  expect(scoreShare(-2, -2)).toBe(50)
  expect(scoreShare(0, -2)).toBe(100)
})
