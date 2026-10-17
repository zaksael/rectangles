import { useState } from 'react'
import { ConnectionLostModal } from './dialogs/ConnectionLostModal'
import { ModeSelectScreen, type StartGameParams } from './screens/ModeSelectScreen'
import { NarrowWindowGate } from './dialogs/NarrowWindowGate'
import { PlayingScreen } from './screens/PlayingScreen'
import { ReplayScreen } from './screens/ReplayScreen'
import { SettingsOverlay } from './dialogs/SettingsOverlay'
import { botName, useGameSocket } from './hooks/useGameSocket'
import { useShiftHeld } from './hooks/useShiftHeld'

type Screen = 'MODE_SELECT' | 'PLAYING' | 'REPLAY'

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
  // Kept here, not in Replay, so it survives leaving and reopening the screen.
  const [showBetterOption, setShowBetterOption] = useState(false)
  const [connectParams, setConnectParams] = useState(IDLE_CONNECT_PARAMS)

  const gameSocket = useGameSocket(connectParams)
  useShiftHeld()

  // The game screen takes over the moment the socket opens (set during render, so Mode Select never shows a frame of the open game).
  if (screen === 'MODE_SELECT' && gameSocket.status === 'open') setScreen('PLAYING')

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
    // The counter keeps counting: the next game's connection must never share an id with the one just left.
    setConnectParams((prev) => ({ ...IDLE_CONNECT_PARAMS, connectionId: prev.connectionId }))
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
      <NarrowWindowGate screen="Playing">
        <PlayingScreen
          state={gameSocket.state}
          error={gameSocket.error}
          sendAction={gameSocket.sendAction}
          onOpenSettings={() => setSettingsOpen(true)}
          onNewGame={handleNewGame}
          onReplay={(fromSeriesResult) => {
            setReplayFromSeriesResult(fromSeriesResult)
            gameSocket.requestAnalysis()
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
      </NarrowWindowGate>
    )
  }

  if (screen === 'REPLAY' && gameSocket.state) {
    return (
      <NarrowWindowGate screen="Replay">
        <ReplayScreen
          game={gameSocket.state.game}
          series={gameSocket.state.series}
          onBack={() => setScreen('PLAYING')}
          analysis={gameSocket.analysis}
          showBetterOption={showBetterOption}
          onToggleBetterOption={() => setShowBetterOption((on) => !on)}
        />
      </NarrowWindowGate>
    )
  }
}

export default App
