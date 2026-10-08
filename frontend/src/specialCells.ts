import type { GameWireState } from './gameTypes'

type SpecialKind = 'prize' | 'pitfall' | 'steal'

// Rule order, which is the order the legend and the status line list kinds in.
const SPECIAL_RULES: { kind: SpecialKind; label: string; sign: string }[] = [
  { kind: 'prize', label: 'Prize', sign: '+' },
  { kind: 'pitfall', label: 'Pitfall', sign: '−' },
  { kind: 'steal', label: 'Steal', sign: '±' },
]

// The rules that are on, each with its point value from the wire.
export function enabledSpecialRules(game: GameWireState) {
  return SPECIAL_RULES.filter(({ kind }) => game.houseRules[kind].enabled).map((rule) => ({ ...rule, points: game.houseRules[rule.kind].points }))
}

// Every cell of a rule that is on, keyed "row,col", with the kind of mark it carries. Owned cells are still in it: the board hides a mark once a piece covers it.
export function specialCellKinds(game: GameWireState): Map<string, SpecialKind> {
  const cells = new Map<string, SpecialKind>()
  for (const { kind } of SPECIAL_RULES) {
    const rule = game.houseRules[kind]
    if (rule.enabled) for (const [r, c] of rule.cells) cells.set(`${r},${c}`, kind)
  }
  return cells
}

// The rules whose cells a w x h piece at topLeft would cover, in rule order, each with its value text ("Pitfall (\u221210)").
export function coveredSpecialRules(game: GameWireState, topLeft: [number, number], dims: [number, number]): string[] {
  const cells = specialCellKinds(game)
  const hit = new Set<SpecialKind>()
  for (let r = topLeft[0]; r < topLeft[0] + dims[1]; r++) {
    for (let c = topLeft[1]; c < topLeft[1] + dims[0]; c++) {
      const kind = cells.get(`${r},${c}`)
      if (kind) hit.add(kind)
    }
  }
  return enabledSpecialRules(game).filter(({ kind }) => hit.has(kind)).map(({ label, sign, points }) => `${label} (${sign}${points})`)
}
