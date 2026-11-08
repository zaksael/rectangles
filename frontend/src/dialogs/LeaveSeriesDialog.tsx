import { useAutoOpenDialog } from '../hooks/useAutoOpenDialog'

interface LeaveSeriesDialogProps {
  onCancel: () => void
  onConfirm: () => void
}

export function LeaveSeriesDialog({ onCancel, onConfirm }: LeaveSeriesDialogProps) {
  const dialogRef = useAutoOpenDialog()

  return (
    // Suppress the native auto-close so Escape routes through the same onCancel as the button.
    <dialog
      className="modal leave-series-confirm"
      ref={dialogRef}
      aria-labelledby="leave-series-title"
      onCancel={(e) => {
        e.preventDefault()
        e.stopPropagation() // React bubbles cancel up the tree, and this dialog sits inside the Menu's
        onCancel()
      }}
    >
      <h2 id="leave-series-title">Leave the series?</h2>
      <p>Rounds played so far aren’t saved, and you return to Mode Select. This can’t be undone.</p>
      <div className="actions">
        <button className="btn secondary" onClick={onCancel} autoFocus>
          Cancel
        </button>
        <button className="btn destructive" onClick={onConfirm}>
          Leave series
        </button>
      </div>
    </dialog>
  )
}
