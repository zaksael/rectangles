import { useEffect, useState } from 'react'
import type { Screen } from './screens'
import { ConnectionLostModal } from './screens/ConnectionLostModal'
import { ModeSelectScreen, type StartGameParams } from './screens/ModeSelectScreen'
import { PlayingScreen } from './screens/PlayingScreen'
import { ReplayScreen } from './screens/ReplayScreen'
import { SettingsOverlay } from './screens/SettingsOverlay'
import { useGameSocket } from './useGameSocket'

const PROTOCOL_VERSION = 1

const IDLE_CONNECT_PARAMS = { protocolVersion: PROTOCOL_VERSION, enabled: false, connectionId: 0 }

function App() {
  const [screen, setScreen] = useState<Screen>('MODE_SELECT')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [connectParams, setConnectParams] = useState(IDLE_CONNECT_PARAMS)

  const gameSocket = useGameSocket(connectParams)

  useEffect(() => {
    if (screen === 'MODE_SELECT' && gameSocket.status === 'open') {
      setScreen('PLAYING')
    }
  }, [screen, gameSocket.status])

  function handleStartGame(params: StartGameParams): void {
    setConnectParams((prev) => ({
      ...params,
      protocolVersion: PROTOCOL_VERSION,
      enabled: true,
      connectionId: prev.connectionId + 1,
    }))
  }

  function handleNewGame(): void {
    gameSocket.disconnect()
    setConnectParams(IDLE_CONNECT_PARAMS)
    setSettingsOpen(false)
    setScreen('MODE_SELECT')
  }

  if (screen === 'MODE_SELECT') {
    return (
      <ModeSelectScreen
        isConnecting={connectParams.enabled && gameSocket.status === undefined}
        connectFailed={gameSocket.status === 'connect-failed'}
        onStartGame={handleStartGame}
      />
    )
  }

  if (screen === 'PLAYING') {
    if (gameSocket.status === 'closed-unexpected') {
      return <ConnectionLostModal isSeries={gameSocket.state?.series !== null} onNewGame={handleNewGame} />
    }
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
