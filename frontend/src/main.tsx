import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

async function render() {
  let root = <App />
  // Dev builds only: `?fixture=<name>` shows the Playing screen over a canned state (see fixtures/devFixtures.ts).
  if (import.meta.env.DEV) {
    const { fixtureNameFromSearch } = await import('./fixtures/devFixtures')
    const name = fixtureNameFromSearch(window.location.search)
    if (name) {
      const { FixtureApp } = await import('./FixtureApp')
      root = <FixtureApp name={name} />
    }
  }
  createRoot(document.getElementById('root')!).render(<StrictMode>{root}</StrictMode>)
}

void render()
