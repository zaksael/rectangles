import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { loadBotSpeed, saveBotSpeed } from './botSpeed'

beforeEach(() => localStorage.clear())
afterEach(() => vi.restoreAllMocks())

test('with nothing stored the bot speed is Normal, 500 ms', () => {
  expect(loadBotSpeed()).toEqual({ label: 'Normal', ms: 500 })
})

test('a saved speed is loaded back', () => {
  saveBotSpeed('Fast')

  expect(loadBotSpeed()).toEqual({ label: 'Fast', ms: 150 })
})

test('an unknown stored value falls back to Normal', () => {
  localStorage.setItem('rectangles.botSpeed:v1', 'Warp')

  expect(loadBotSpeed().label).toBe('Normal')
})

test('storage that throws gives Normal on load and is ignored on save', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('blocked')
  })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('blocked')
  })

  expect(loadBotSpeed().label).toBe('Normal')
  expect(() => saveBotSpeed('Slow')).not.toThrow()
})
