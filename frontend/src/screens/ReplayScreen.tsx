interface ReplayScreenProps {
  onBack: () => void
}

export function ReplayScreen({ onBack }: ReplayScreenProps) {
  return (
    <div>
      <p>Replay</p>
      <button onClick={onBack}>Back</button>
    </div>
  )
}
