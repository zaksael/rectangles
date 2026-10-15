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
  // One plain line shown under the label on Mode Select.
  description: string
}

interface HouseRuleGroup {
  label: string
  rules: HouseRuleDef[]
}

export const HOUSE_RULE_GROUPS: HouseRuleGroup[] = [
  {
    label: 'Special cells',
    rules: [
      {
        key: 'prizeEnabled',
        label: 'Prize',
        description: 'Cover a prize cell to bank a 10-point bonus.',
      },
      {
        key: 'pitfallEnabled',
        label: 'Pitfall',
        description: 'Cover a pitfall cell and lose 10 points.',
      },
      {
        key: 'stealEnabled',
        label: 'Steal',
        description: 'Cover a steal cell to take 10 points from your opponent.',
      },
    ],
  },
  {
    label: 'Board setup',
    rules: [
      {
        key: 'wallsEnabled',
        label: 'Walls',
        description: 'Walls sit between cells and block pieces; build around their ends.',
      },
      {
        key: 'obstaclesEnabled',
        label: 'Obstacles',
        description: 'Some cells are blocked for the whole match.',
      },
      {
        key: 'selfEnclosedPenaltyEnabled',
        label: 'Enclosure penalty',
        description: 'Each empty cell you wall off by yourself costs 1 point.',
      },
    ],
  },
  {
    label: 'Dice & turn',
    rules: [
      {
        key: 'wildcardEnabled',
        label: 'Wildcard roll',
        description: 'On doubles, change one die to any value from 1 to 6.',
      },
      {
        key: 'rerollEnabled',
        label: 'Reroll',
        description: 'Discard a roll and roll again, twice per game.',
      },
      {
        key: 'comebackNudgeEnabled',
        label: 'Comeback',
        description: 'Far behind? You earn one extra reroll.',
      },
    ],
  },
]
