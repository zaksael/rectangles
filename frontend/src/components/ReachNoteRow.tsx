export const REACH_NOTE_ID = 'reach-note'

// The line under an In reach row; the row's header names it with aria-describedby.
export function ReachNoteRow() {
  return (
    <tr className="note-row">
      <td colSpan={3} id={REACH_NOTE_ID}>Cells each could still build on; counts overlap</td>
    </tr>
  )
}
