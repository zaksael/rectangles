export interface HouseRules {
  prizeEnabled: boolean
  pitfallEnabled: boolean
  stealEnabled: boolean
  wallsEnabled: boolean
  obstaclesEnabled: boolean
  selfEnclosedPenaltyEnabled: boolean
  wildcardEnabled: boolean
  rerollEnabled: boolean
  comebackNudgeEnabled: boolean
}

interface HouseRuleDef {
  key: keyof HouseRules
  label: string
  // Flip to true when the Playing screen supports the rule; until then it is
  // neither shown on Mode Select nor sent to the server.
  implemented: boolean
}

interface HouseRuleGroup {
  label: string
  rules: HouseRuleDef[]
}

export const HOUSE_RULE_GROUPS: HouseRuleGroup[] = [
  {
    label: 'Special cells',
    rules: [
      { key: 'prizeEnabled', label: 'Prize', implemented: true },
      { key: 'pitfallEnabled', label: 'Pitfall', implemented: true },
      { key: 'stealEnabled', label: 'Steal', implemented: true },
    ],
  },
  {
    label: 'Board setup',
    rules: [
      { key: 'wallsEnabled', label: 'Walls', implemented: true },
      { key: 'obstaclesEnabled', label: 'Obstacles', implemented: true },
      {
        key: 'selfEnclosedPenaltyEnabled',
        label: 'Enclosure penalty',
        implemented: true,
      },
    ],
  },
  {
    label: 'Dice & turn',
    rules: [
      { key: 'wildcardEnabled', label: 'Wildcard roll', implemented: true },
      { key: 'rerollEnabled', label: 'Reroll', implemented: true },
      { key: 'comebackNudgeEnabled', label: 'Comeback', implemented: true },
    ],
  },
]

export function implementedGroups(): HouseRuleGroup[] {
  return HOUSE_RULE_GROUPS.map((g) => ({ ...g, rules: g.rules.filter((r) => r.implemented) })).filter(
    (g) => g.rules.length > 0,
  )
}

export function implementedHouseRules(rules: HouseRules): Partial<HouseRules> {
  return Object.fromEntries(
    implementedGroups()
      .flatMap((g) => g.rules)
      .map((r) => [r.key, rules[r.key]]),
  )
}
