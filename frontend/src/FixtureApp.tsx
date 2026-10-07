import { useEffect } from 'react'
import { buildFixture } from './fixtures/devFixtures'
import { PlayingScreen } from './screens/PlayingScreen'

// Dev-only: the real Playing screen over a canned state. Actions are logged, not sent anywhere.
export function FixtureApp({ name }: { name: string }) {
  const state = buildFixture(name)
  useEffect(() => {
    console.info(`fixture "${name}" is active: actions are ignored`)
  }, [name])
  if (!state) return null
  return (
    <PlayingScreen
      state={state}
      error={null}
      sendAction={(action) => console.info('fixture ignored action', JSON.stringify(action))}
      onOpenSettings={() => {}}
      onNewGame={() => {}}
    />
  )
}
