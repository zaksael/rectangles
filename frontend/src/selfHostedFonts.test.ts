import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('the page loads no font or stylesheet from another origin, so the bundle works offline and under a strict CSP', () => {
  expect(read('../index.html')).not.toMatch(/https?:\/\//)
})

test('every face tokens.css names (Plex Sans 400/500/600, Plex Mono 500, Source Serif 4 600) ships in the bundle', () => {
  const main = read('./main.tsx')
  for (const face of [
    '@fontsource/ibm-plex-sans/latin-400.css',
    '@fontsource/ibm-plex-sans/latin-500.css',
    '@fontsource/ibm-plex-sans/latin-600.css',
    '@fontsource/ibm-plex-mono/latin-500.css',
    '@fontsource/source-serif-4/latin-600.css',
  ]) {
    expect(main).toContain(`import '${face}'`)
  }
})
