import { Component, type ReactNode } from 'react'
import '../dialogs/NarrowWindowGate.css'

// A render error unmounts the whole tree to a blank page. A reload is the only safe reset, since whatever state caused it is suspect.
// The card is plain markup with no app state, so it cannot throw for the reason the app did, and it reuses the narrow-window notice's look.
export class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (!this.state.failed) return this.props.children
    return (
      <div className="narrow-notice" role="alert">
        <div className="narrow-notice-body">
          <div className="narrow-notice-reason">Something broke</div>
          <h1 className="title narrow-notice-title">Something Went Wrong</h1>
          <p className="narrow-notice-text">The page stopped working. Reload to start again.</p>
          <div className="narrow-notice-actions">
            <button className="btn primary" type="button" onClick={() => window.location.reload()}>
              Reload
            </button>
          </div>
        </div>
      </div>
    )
  }
}
