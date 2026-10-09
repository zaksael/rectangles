import { useEffect, useState } from 'react'
import type { Screen } from './screens'
import { ConnectionLostModal } from './screens/ConnectionLostModal'
import { ModeSelectScreen, type StartGameParams } from './screens/ModeSelectScreen'
import { PlayingScreen } from './screens/PlayingScreen'
import { ReplayScreen } from './screens/ReplayScreen'
import { SettingsOverlay } from './screens/SettingsOverlay'
import { botName, useGameSocket } from './useGameSocket'
import { useShiftHeld } from './useShiftHeld'

const PROTOCOL_VERSION = 1

const IDLE_CONNECT_PARAMS: Pick<StartGameParams, 'botSeats' | 'botDifficulty'> & {
  protocolVersion: number
  enabled: boolean
  connectionId: number
} = {
  protocolVersion: PROTOCOL_VERSION,
  enabled: false,
  connectionId: 0,
}

function App() {
  const [screen, setScreen] = useState<Screen>('MODE_SELECT')
  const [settingsOpen, setSettingsOpen] = useState(false)
  // Back from Replay shows the card Replay was opened from; only the series card differs from the default.
  const [replayFromSeriesResult, setReplayFromSeriesResult] = useState(false)
  const [connectParams, setConnectParams] = useState(IDLE_CONNECT_PARAMS)

  const gameSocket = useGameSocket(connectParams)
  useShiftHeld()

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
    setReplayFromSeriesResult(false)
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
        <PlayingScreen
          state={gameSocket.state}
          error={gameSocket.error}
          sendAction={gameSocket.sendAction}
          onOpenSettings={() => setSettingsOpen(true)}
          onNewGame={handleNewGame}
          onReplay={(fromSeriesResult) => {
            setReplayFromSeriesResult(fromSeriesResult)
            setScreen('REPLAY')
          }}
          initialSeriesResultOpen={replayFromSeriesResult}
          botSeat={connectParams.botSeats}
        />
        {settingsOpen && gameSocket.state && (
          <SettingsOverlay
            game={gameSocket.state.game}
            series={gameSocket.state.series}
            opponentLabel={connectParams.botSeats ? botName(connectParams.botDifficulty) : 'Local 2P'}
            sendAction={gameSocket.sendAction}
            botSeat={connectParams.botSeats}
            onClose={() => setSettingsOpen(false)}
          />
        )}
      </>
    )
  }

  if (screen === 'REPLAY' && gameSocket.state) {
    return <ReplayScreen game={gameSocket.state.game} onBack={() => setScreen('PLAYING')} />
  }
}

export default App
