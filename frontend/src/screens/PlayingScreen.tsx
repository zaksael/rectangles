interface PlayingScreenProps {
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
