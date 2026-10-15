import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { HOUSE_RULE_GROUPS, type HouseRules } from './houseRules'
import { SELF_ENCLOSED_PENALTY_PER_CELL } from './ruleRows'

test('every house rule has a one-line description for Mode Select', () => {
  const rules = HOUSE_RULE_GROUPS.flatMap((g) => g.rules)

  expect(rules).toHaveLength(9)
  for (const rule of rules) expect(rule.description?.trim().length ?? 0, rule.label).toBeGreaterThan(0)
})

// Mode Select runs before any state arrives, so the descriptions carry the engine's numbers as text; these tests read the engine's
// constants file so a changed value fails here instead of leaving the copy quietly wrong.
const constantsPy = readFileSync('../rectangles/engine/constants.py', 'utf8')
const engine = (name: string): number => {
  const value = constantsPy.match(new RegExp(`^${name} = (\\d+)`, 'm'))?.[1]
  if (value === undefined) throw new Error(`${name} not found in rectangles/engine/constants.py`)
  return Number(value)
}
const descriptionOf = (key: keyof HouseRules) => HOUSE_RULE_GROUPS.flatMap((g) => g.rules).find((r) => r.key === key)!.description
const words = ['zero', 'one', 'two', 'three']
const times = (n: number) => ({ 1: 'once', 2: 'twice', 3: 'three times' })[n as 1 | 2 | 3]
const plural = (n: number, noun: string) => `${n} ${noun}${n === 1 ? '' : 's'}`

test.each([
  ['prizeEnabled', () => `${engine('PRIZE_BONUS_POINTS')}-point bonus`],
  ['pitfallEnabled', () => `lose ${plural(engine('PITFALL_PENALTY_POINTS'), 'point')}`],
  ['stealEnabled', () => `take ${plural(engine('STEAL_POINTS'), 'point')}`],
  ['wildcardEnabled', () => `from ${engine('DICE_MIN')} to ${engine('DICE_MAX')}`],
  ['rerollEnabled', () => `${times(engine('REROLL_LIMIT'))} per game`],
  ['selfEnclosedPenaltyEnabled', () => `costs ${plural(engine('SELF_ENCLOSED_PENALTY_PER_CELL'), 'point')}`],
  ['comebackNudgeEnabled', () => `${words[engine('COMEBACK_NUDGE_EXTRA_REROLLS')]} extra reroll${engine('COMEBACK_NUDGE_EXTRA_REROLLS') === 1 ? '' : 's'}`],
] as [keyof HouseRules, () => string][])('the %s description states the engine\'s current number', (key, expected) => {
  expect(descriptionOf(key)).toContain(expected())
})

test('the Enclosure rate the result card and Replay use is the engine\'s', () => {
  expect(SELF_ENCLOSED_PENALTY_PER_CELL).toBe(engine('SELF_ENCLOSED_PENALTY_PER_CELL'))
})
