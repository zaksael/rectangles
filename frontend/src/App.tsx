import { useState } from 'react'
import type { Screen } from './screens'
import { ModeSelectScreen } from './screens/ModeSelectScreen'
import { PlayingScreen } from './screens/PlayingScreen'
import { ReplayScreen } from './screens/ReplayScreen'
import { SettingsOverlay } from './screens/SettingsOverlay'

function App() {
  const [screen, setScreen] = useState<Screen>('MODE_SELECT')
  const [settingsOpen, setSettingsOpen] = useState(false)

  if (screen === 'MODE_SELECT') {
    return <ModeSelectScreen onStartGame={() => setScreen('PLAYING')} />
  }

  if (screen === 'PLAYING') {
    return (
      <>
        <PlayingScreen onOpenSettings={() => setSettingsOpen(true)} onGoToReplay={() => setScreen('REPLAY')} />
        {settingsOpen && <SettingsOverlay onClose={() => setSettingsOpen(false)} />}
      </>
    )
  }

  if (screen === 'REPLAY') {
    return <ReplayScreen onBack={() => setScreen('PLAYING')} />
  }

  return null
}

export default App
