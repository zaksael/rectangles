import { useEffect, useState } from 'react'
import { buildFixture } from './fixtures/devFixtures'
import { NarrowWindowGate } from './screens/NarrowWindowGate'
import { PlayingScreen } from './screens/PlayingScreen'
import { ReplayScreen } from './screens/ReplayScreen'

// Dev-only: the real Playing screen over a canned state. Actions are logged, not sent anywhere.
export function FixtureApp({ name }: { name: string }) {
  const state = buildFixture(name)
  const [replaying, setReplaying] = useState(false)
  const [fromSeriesResult, setFromSeriesResult] = useState(false)
  useEffect(() => {
    console.info(`fixture "${name}" is active: actions are ignored`)
  }, [name])
  if (!state) return null
  if (replaying) {
    return (
      <NarrowWindowGate screen="Replay">
        <ReplayScreen game={state.game} onBack={() => setReplaying(false)} />
      </NarrowWindowGate>
    )
  }
  return (
    <NarrowWindowGate screen="Playing">
      <PlayingScreen
        state={state}
        error={null}
        sendAction={(action) => console.info('fixture ignored action', JSON.stringify(action))}
        onOpenSettings={() => {}}
        onNewGame={() => {}}
        onReplay={(fromResult) => {
          setFromSeriesResult(fromResult)
          setReplaying(true)
        }}
        initialSeriesResultOpen={fromSeriesResult}
      />
    </NarrowWindowGate>
  )
}
