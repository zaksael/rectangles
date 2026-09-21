import type { GameAction } from '../gameTypes'
import type { GameError, GameState } from '../useGameSocket'

interface PlayingScreenProps {
  state: GameState | null
  error: GameError | null
  sendAction: (action: GameAction) => void
  onOpenSettings: () => void
  onGoToReplay: () => void
}

export function PlayingScreen({ onOpenSettings, onGoToReplay }: PlayingScreenProps) {
  return (
    <div>
      <p>Playing</p>
      <button className="btn secondary" onClick={onOpenSettings}>
        Pause
      </button>
      <button className="btn secondary" onClick={onGoToReplay}>
        Replay
      </button>
    </div>
  )
}
