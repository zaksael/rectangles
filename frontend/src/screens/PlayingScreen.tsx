import { useEffect, useRef } from 'react'
import { Board } from '../components/Board'
import type { GameAction } from '../gameTypes'
import { usePlacementInput } from '../usePlacementInput'
import type { GameError, GameState } from '../useGameSocket'
import './PlayingScreen.css'

interface PlayingScreenProps {
  state: GameState | null
  error: GameError | null
  sendAction: (action: GameAction) => void
  onOpenSettings: () => void
  onGoToReplay: () => void
}

export function PlayingScreen({ state, sendAction, onOpenSettings, onGoToReplay }: PlayingScreenProps) {
  const turnState = state?.game.turn.turnState

  const sendActionRef = useRef(sendAction)
  sendActionRef.current = sendAction

  const { rotate, previewTopLeft, previewKind, coverableCells, dims, handleCellHover, handleCellTap } = usePlacementInput(
    state?.game ?? null,
    sendAction,
  )
  const rotateRef = useRef(rotate)
  rotateRef.current = rotate

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'd' && turnState === 'awaitingRoll') {
        sendActionRef.current({ type: 'roll' })
      } else if (event.key === 'r' && turnState === 'choosingPlacement') {
        rotateRef.current()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [turnState])

  return (
    <div className="frame">
      {state && (
        <>
          <div className="header">
            {(['1', '2'] as const).map((id) => (
              <div
                key={id}
                className={`player p${id}${state.game.turn.currentPlayerId === Number(id) ? ' current' : ''}`}
              >
                <span className="dot" />
                <span className="name">{state.game.players[id].name}</span>
              </div>
            ))}
          </div>
          <Board
            game={state.game}
            previewTopLeft={previewTopLeft}
            previewDims={dims}
            previewKind={previewKind}
            coverableCells={coverableCells}
            onCellHover={turnState === 'choosingPlacement' ? handleCellHover : undefined}
            onCellTap={turnState === 'choosingPlacement' ? handleCellTap : undefined}
          />
        </>
      )}
      <div className="toolbar-actions">
        {turnState === 'awaitingRoll' && (
          <button className="btn primary" onClick={() => sendAction({ type: 'roll' })}>
            Roll
          </button>
        )}
        {state && turnState !== 'awaitingRoll' && state.game.turn.lastRoll && (
          <div className="dice">
            {state.game.turn.lastRoll.map((value, i) => (
              <span key={i} className="die">
                {value}
              </span>
            ))}
          </div>
        )}
        {turnState === 'choosingPlacement' && (
          <button className="btn secondary" onClick={rotate}>
            Rotate
          </button>
        )}
        {turnState === 'skipped' && (
          <button className="btn danger-outline" onClick={() => sendAction({ type: 'skip' })}>
            Skip
          </button>
        )}
        <button className="btn secondary pause" onClick={onOpenSettings}>
          Pause
        </button>
        <button className="btn secondary" onClick={onGoToReplay}>
          Replay
        </button>
      </div>
    </div>
  )
}
