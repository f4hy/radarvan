import Alert from "@mui/material/Alert"
import Snackbar from "@mui/material/Snackbar"
import * as React from "react"

export function useErrorSnackbar() {
  const [message, setMessage] = React.useState<string | null>(null)

  const showError = React.useCallback((e: unknown) => {
    setMessage(e instanceof Error ? e.message : String(e))
  }, [])

  const errorSnackbar = (
    <Snackbar
      open={message !== null}
      autoHideDuration={6000}
      onClose={() => setMessage(null)}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
    >
      <Alert
        severity="error"
        onClose={() => setMessage(null)}
        sx={{ width: "100%" }}
      >
        {message}
      </Alert>
    </Snackbar>
  )

  return { showError, errorSnackbar }
}
