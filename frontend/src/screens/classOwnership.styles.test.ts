import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { readCss } from '../dev/testUtils/styles'

const SCREENS = ['ModeSelectScreen', 'PlayingScreen', 'ReplayScreen']

// Classes a stylesheet styles on their own, i.e. at the start of a selector (`.playing {`, `.playing .rail`).
const rootClasses = (css: string) => new Set([...css.matchAll(/(?:^|[,{};])\s*\.([a-z][\w-]*)/g)].map(m => m[1]!))

// The words of every string literal in a className attribute, and of a template's static text; never an identifier inside `${}`.
function classNamesIn(tsx: string) {
  const out = new Set<string>()
  for (const at of tsx.matchAll(/className=/g)) {
    const start = at.index! + at[0].length
    let end = start
    if (tsx[start] === '"') end = tsx.indexOf('"', start + 1) + 1
    else for (let depth = 0; end < tsx.length; end++) {
      if (tsx[end] === '{') depth++
      if (tsx[end] === '}' && --depth === 0) { end++; break }
    }
    const expr = tsx.slice(start, end)
    const literals = [...expr.matchAll(/(['"])([^'"`$]*)\1/g)].map(m => m[2]!)
    const templates = [...expr.matchAll(/`([^`]*)`/g)].map(m => m[1]!.replace(/\$\{[^}]*\}/g, ' '))
    for (const text of [...literals, ...templates]) for (const word of text.split(/\s+/)) if (word) out.add(word)
  }
  return out
}

// The classes a screen writes that another screen's stylesheet owns, and its own stylesheet does not: the other screen's rule would style them.
export function borrowedClasses(tsx: string, ownCss: string, otherCss: string[], sharedCss: string[] = []) {
  const own = new Set([...rootClasses(ownCss), ...sharedCss.flatMap(css => [...rootClasses(css)])])
  const theirs = new Set(otherCss.flatMap(css => [...rootClasses(css)]))
  return [...classNamesIn(tsx)].filter(name => theirs.has(name) && !own.has(name)).sort()
}

test('a screen that writes a class another screen styles on its own is caught', () => {
  const playingCss = '.playing { display: grid }\n.playing .rail { gap: 0 }'

  expect(borrowedClasses('<main className="playing">', '.replay { gap: 0 }', [playingCss])).toEqual(['playing'])
})

test('a class the screen styles itself is not flagged, even when another screen styles the same name', () => {
  expect(borrowedClasses('<main className="playing">', '.playing { gap: 0 }', ['.playing { display: grid }'])).toEqual([])
})

test('a class another screen only uses as a modifier, and a state variable with the same name, are not flagged', () => {
  const scoped = '.score-table th:not(.over) { gap: 0 }'

  expect(borrowedClasses('<th className="over">', '.replay {}', [scoped])).toEqual([])
  expect(borrowedClasses('<b className={`btn${playing ? \' on\' : \'\'}`} />', '.replay {}', ['.playing { gap: 0 }'])).toEqual([])
})

const SHARED = ['Board.css', 'ScoreTable.css', 'NarrowWindowGate.css', 'index.css', 'tokens.css'].map(readCss)

// Known leaks, each with the rule that causes it: remove the entry when the rule is scoped.
const KNOWN: Record<string, string[]> = {
  // PlayingScreen.css `.rail-head .btn` in the coarse-pointer block is not scoped under `.playing`.
  ReplayScreen: ['rail-head'],
}

test.each(SCREENS)('%s writes no class that another screen\'s stylesheet styles on its own', screen => {
  const others = SCREENS.filter(s => s !== screen).map(s => readCss(`${s}.css`))
  const found = borrowedClasses(readFileSync(`src/screens/${screen}.tsx`, 'utf8'), readCss(`${screen}.css`), others, SHARED)

  expect(found.filter(name => !KNOWN[screen]?.includes(name))).toEqual([])
})

test('a class a shared stylesheet owns is not borrowed, even when a screen also styles it', () => {
  const shared = ['.score-table { width: 100% }']

  expect(borrowedClasses('<table className="score-table">', '.replay {}', ['.score-table .last-skip { gap: 0 }'], shared)).toEqual([])
})

test('a class inside a template literal or a conditional is caught', () => {
  const playingCss = '.playing { display: grid }'
  const pause = '<button className={`btn playing${on ? \' replay-on\' : \'\'}`}>'

  expect(borrowedClasses(pause, '.replay {}', [playingCss])).toEqual(['playing'])
  expect(borrowedClasses('<b className={on ? \'playing\' : \'x\'} />', '.replay {}', [playingCss])).toEqual(['playing'])
})
