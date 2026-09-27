import { useAutoOpenDialog } from '../useAutoOpenDialog'

interface ResetConfirmDialogProps {
  onCancel: () => void
  onConfirm: () => void
}

export function ResetConfirmDialog({ onCancel, onConfirm }: ResetConfirmDialogProps) {
  const dialogRef = useAutoOpenDialog()

  return (
    // Suppress the native auto-close so Escape routes through the same onCancel as the button.
    <dialog
      className="modal reset-confirm"
      ref={dialogRef}
      aria-labelledby="reset-title"
      onCancel={(e) => {
        e.preventDefault()
        onCancel()
      }}
    >
      <h2 id="reset-title">Reset to defaults?</h2>
      <p>Board size, skip limit, and house rules go back to their defaults. Your chosen opponent stays selected.</p>
      <div className="actions">
        <button className="btn secondary" onClick={onCancel} autoFocus>
          Cancel
        </button>
        <button className="btn destructive" onClick={onConfirm}>
          Reset
        </button>
      </div>
    </dialog>
  )
}
