import { useEffect, useRef } from 'react'

// Opens the dialog as a modal on mount. When it unmounts, focus goes back to whatever had it
// before (the button that opened it), so a keyboard user keeps their place.
export function useAutoOpenDialog<T extends HTMLDialogElement>() {
  const ref = useRef<T>(null)
  // Read on the first render: by the time an effect runs the dialog may already hold focus
  // (an autofocused button, or StrictMode's second run once the page behind it is inert).
  const opener = useRef(document.activeElement)
  useEffect(() => {
    ref.current?.showModal()
    return () => {
      if (opener.current instanceof HTMLElement && opener.current.isConnected) opener.current.focus()
    }
  }, [])
  return ref
}
