import Alert from "@mui/material/Alert"
import Snackbar from "@mui/material/Snackbar"
import * as React from "react"
import { errorMessage } from "./apiError"

export function useErrorSnackbar() {
  const [message, setMessage] = React.useState<string | null>(null)

  const showError = React.useCallback((e: unknown) => {
    setMessage(errorMessage(e))
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
