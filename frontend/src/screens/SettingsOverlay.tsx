interface SettingsOverlayProps {
  onClose: () => void
}

export function SettingsOverlay({ onClose }: SettingsOverlayProps) {
  return (
    <div>
      <p>Settings</p>
      <button className="btn secondary" onClick={onClose}>
        Close
      </button>
    </div>
  )
}
