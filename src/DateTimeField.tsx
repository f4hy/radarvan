import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs"
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker"
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider"
import type * as React from "react"

// @mui/x-date-pickers is ~160 kB and only two admin-only controls use it (the
// Agenda row scheduler and the bracket reveal-time dialog), so the
// LocalizationProvider lives here beside them rather than at the App root —
// that keeps the whole package out of the initial bundle for everyone else.
export default function DateTimeField(
  props: React.ComponentProps<typeof DateTimePicker>,
) {
  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <DateTimePicker {...props} />
    </LocalizationProvider>
  )
}
