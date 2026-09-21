import { useEffect, useRef } from 'react'

interface SettingsOverlayProps {
  onClose: () => void
}

export function SettingsOverlay({ onClose }: SettingsOverlayProps) {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    dialogRef.current?.showModal()
  }, [])

  return (
    // Suppress the native auto-close so Escape routes through the same onClose as the button.
    <dialog
      ref={dialogRef}
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
    >
      <p>Settings</p>
      <button className="btn secondary" onClick={onClose}>
        Close
      </button>
    </dialog>
  )
}
