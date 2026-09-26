import { useAutoOpenDialog } from '../useAutoOpenDialog'

interface ConnectionLostModalProps {
  isSeries: boolean
  onNewGame: () => void
}

export function ConnectionLostModal({ isSeries, onNewGame }: ConnectionLostModalProps) {
  const dialogRef = useAutoOpenDialog()

  const body = isSeries
    ? "The connection to the server dropped and couldn't be restored. Rejoining an in-progress game isn't supported yet, and the series can't be resumed either — you'll need to start a new one."
    : "The connection to the server dropped and couldn't be restored. Rejoining an in-progress game isn't supported yet — you'll need to start a new one."

  return (
    // Escape has no dismiss action here (only "New Game" clears this state), so cancel is suppressed.
    <dialog
      className="modal connection-lost"
      ref={dialogRef}
      aria-labelledby="connection-lost-title"
      onCancel={(e) => e.preventDefault()}
    >
      <p className="reason">Connection lost</p>
      <h2 id="connection-lost-title">This game can&apos;t be resumed</h2>
      <p className="body">{body}</p>
      <div className="actions">
        <button className="btn primary" onClick={onNewGame} autoFocus>
          New Game
        </button>
      </div>
    </dialog>
  )
}
