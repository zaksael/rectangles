import { useEffect, useRef } from 'react'
import { Board } from '../components/Board'
import type { GameAction } from '../gameTypes'
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

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'd' && turnState === 'awaitingRoll') {
        sendActionRef.current({ type: 'roll' })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [turnState])

  return (
    <div>
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
          <Board game={state.game} />
          <div className="toolbar-actions">
            {turnState === 'awaitingRoll' ? (
              <button className="btn primary" onClick={() => sendAction({ type: 'roll' })}>
                Roll
              </button>
            ) : (
              state.game.turn.lastRoll && (
                <div className="dice">
                  {state.game.turn.lastRoll.map((value, i) => (
                    <span key={i} className="die">
                      {value}
                    </span>
                  ))}
                </div>
              )
            )}
          </div>
        </>
      )}
      <button className="btn secondary pause" onClick={onOpenSettings}>
        Pause
      </button>
      <button className="btn secondary" onClick={onGoToReplay}>
        Replay
      </button>
    </div>
  )
}
