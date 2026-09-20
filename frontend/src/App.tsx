import { useState } from 'react'
import type { Screen } from './screens'
import { ConnectionLostModal } from './screens/ConnectionLostModal'
import { ModeSelectScreen } from './screens/ModeSelectScreen'
import { PlayingScreen } from './screens/PlayingScreen'
import { ReplayScreen } from './screens/ReplayScreen'
import { SettingsOverlay } from './screens/SettingsOverlay'
import { useGameSocket } from './useGameSocket'

interface PlayingContainerProps {
  onGoToReplay: () => void
  onNewGame: () => void
}

// Connects only while Playing is mounted - navigating to Replay unmounts this
// and closes the socket. Keeping the connection alive across Replay (the
// server itself doesn't close it) is future scope, not this component's job.
function PlayingContainer({ onGoToReplay, onNewGame }: PlayingContainerProps) {
  const [settingsOpen, setSettingsOpen] = useState(false)
  const gameSocket = useGameSocket({ protocolVersion: 1 })

  if (gameSocket.status === 'closed-unexpected') {
    return <ConnectionLostModal isSeries={gameSocket.state?.series !== null} onNewGame={onNewGame} />
  }

  return (
    <>
      <PlayingScreen onOpenSettings={() => setSettingsOpen(true)} onGoToReplay={onGoToReplay} />
      {settingsOpen && <SettingsOverlay onClose={() => setSettingsOpen(false)} />}
    </>
  )
}

function App() {
  const [screen, setScreen] = useState<Screen>('MODE_SELECT')

  if (screen === 'MODE_SELECT') {
    return <ModeSelectScreen onStartGame={() => setScreen('PLAYING')} />
  }

  if (screen === 'PLAYING') {
    return <PlayingContainer onGoToReplay={() => setScreen('REPLAY')} onNewGame={() => setScreen('MODE_SELECT')} />
  }

  if (screen === 'REPLAY') {
    return <ReplayScreen onBack={() => setScreen('PLAYING')} />
  }

  return null
}

export default App
