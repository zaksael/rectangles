interface PlayingScreenProps {
  onOpenSettings: () => void
  onGoToReplay: () => void
}

export function PlayingScreen({ onOpenSettings, onGoToReplay }: PlayingScreenProps) {
  return (
    <div>
      <p>Playing</p>
      <button onClick={onOpenSettings}>Pause</button>
      <button onClick={onGoToReplay}>Replay</button>
    </div>
  )
}
