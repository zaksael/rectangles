interface ModeSelectScreenProps {
  onStartGame: () => void
}

export function ModeSelectScreen({ onStartGame }: ModeSelectScreenProps) {
  return (
    <div>
      <p>Mode Select</p>
      <button onClick={onStartGame}>Start Game</button>
    </div>
  )
}
