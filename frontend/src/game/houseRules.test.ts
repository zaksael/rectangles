import { expect, test } from 'vitest'
import { HOUSE_RULE_GROUPS } from './houseRules'

test('every house rule has a one-line description for Mode Select', () => {
  const rules = HOUSE_RULE_GROUPS.flatMap((g) => g.rules)

  expect(rules).toHaveLength(9)
  for (const rule of rules) expect(rule.description?.trim().length ?? 0, rule.label).toBeGreaterThan(0)
})
