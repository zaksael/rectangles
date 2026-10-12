import { describe, expect, it } from 'vitest'
import { ruleFor } from './styles'

const css = `.a { color: red; }
tfoot td,
.play.playing, .speed { gap: 2px; }
.play { gap: 9px; }
.play.playing-x { gap: 7px; }
`

describe('ruleFor', () => {
  it('finds a rule whose selector starts a line', () => {
    expect(ruleFor(css, '.a')).toContain('color: red')
  })
  it('finds a selector inside a comma list, on any line or position', () => {
    for (const selector of ['tfoot td', '.play.playing', '.speed']) expect(ruleFor(css, selector)).toContain('gap: 2px')
  })
  it('does not match a longer selector that merely starts the same', () => {
    expect(ruleFor(css, '.play')).toContain('gap: 9px')
    expect(() => ruleFor(css, '.play.pla')).toThrow('no rule')
  })
})
