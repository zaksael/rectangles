import { useEffect, useRef } from 'react'

// Opens the dialog as a modal on mount. When it unmounts, focus goes back to whatever had it
// before (the button that opened it), so a keyboard user keeps their place.
export function useAutoOpenDialog<T extends HTMLDialogElement>() {
  const ref = useRef<T>(null)
  // Read on the first render: by the time an effect runs the dialog may already hold focus
  // (an autofocused button, or StrictMode's second run once the page behind it is inert).
  const opener = useRef(document.activeElement)
  useEffect(() => {
    const dialog = ref.current
    dialog?.showModal()
    // A click on the scrim lands on the dialog element itself, as does one on its padding, so the point must also be
    // outside the box. It acts as Esc: the dialog's own onCancel decides (a locked dialog calls preventDefault there
    // and stays open). Only a press that also began on the scrim counts, so a drag from inside out to it does not dismiss.
    let pressedOnScrim = false
    const onPointerDown = (e: PointerEvent) => {
      const box = dialog?.getBoundingClientRect()
      pressedOnScrim = e.target === dialog && !!box && (e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom)
    }
    const onClick = (e: MouseEvent) => {
      if (pressedOnScrim && e.target === dialog) dialog?.dispatchEvent(new Event('cancel', { cancelable: true }))
      pressedOnScrim = false
    }
    dialog?.addEventListener('pointerdown', onPointerDown)
    dialog?.addEventListener('click', onClick)
    const previous = opener.current
    return () => {
      dialog?.removeEventListener('pointerdown', onPointerDown)
      dialog?.removeEventListener('click', onClick)
      // Only when focus fell to the page: a replacement that took it as the dialog went (an autofocused button) keeps it.
      const focusLost = !document.activeElement || document.activeElement === document.body
      if (focusLost && previous instanceof HTMLElement && previous.isConnected) previous.focus()
    }
  }, [])
  return ref
}
