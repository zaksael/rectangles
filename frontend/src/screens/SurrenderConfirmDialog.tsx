import { useAutoOpenDialog } from '../useAutoOpenDialog'

interface SurrenderConfirmDialogProps {
  opponentName: string
  isSeries: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function SurrenderConfirmDialog({ opponentName, isSeries, onCancel, onConfirm }: SurrenderConfirmDialogProps) {
  const dialogRef = useAutoOpenDialog()

  return (
    // Suppress the native auto-close so Escape routes through the same onCancel as the button.
    <dialog
      className="modal surrender-confirm"
      ref={dialogRef}
      aria-labelledby="surrender-title"
      onCancel={(e) => {
        e.preventDefault()
        onCancel()
      }}
    >
      <h2 id="surrender-title">{isSeries ? 'Surrender this round?' : 'Surrender the match?'}</h2>
      <p>
        {opponentName} wins {isSeries ? 'this round ' : ''}immediately, regardless of the current score.
        {isSeries && ' The series continues to the next round.'} This can’t be undone.
      </p>
      <div className="actions">
        <button className="btn secondary" onClick={onCancel} autoFocus>
          Cancel
        </button>
        <button className="btn destructive" onClick={onConfirm}>
          Surrender
        </button>
      </div>
    </dialog>
  )
}
