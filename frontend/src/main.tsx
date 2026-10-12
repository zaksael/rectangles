import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@fontsource/ibm-plex-sans/latin-400.css'
import '@fontsource/ibm-plex-sans/latin-500.css'
import '@fontsource/ibm-plex-sans/latin-600.css'
import '@fontsource/ibm-plex-mono/latin-500.css'
import '@fontsource/source-serif-4/latin-600.css'
import './index.css'
import App from './App.tsx'

async function render() {
  let root = <App />
  // Dev builds only: `?fixture=<name>` shows the Playing screen over a canned state (see dev/fixtures/devFixtures.ts).
  if (import.meta.env.DEV) {
    const { fixtureNameFromSearch } = await import('./dev/fixtures/devFixtures')
    const name = fixtureNameFromSearch(window.location.search)
    if (name) {
      const { FixtureApp } = await import('./FixtureApp')
      root = <FixtureApp name={name} />
    }
  }
  createRoot(document.getElementById('root')!).render(<StrictMode>{root}</StrictMode>)
}

void render()
