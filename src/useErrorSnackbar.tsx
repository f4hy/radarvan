import Alert from "@mui/material/Alert"
import Snackbar from "@mui/material/Snackbar"
import * as React from "react"
import { errorMessage } from "./apiError"

export function useErrorSnackbar() {
  const [message, setMessage] = React.useState<string | null>(null)

  // Async because reading FastAPI's `detail` off a ResponseError means reading
  // the response body. `showError` itself stays fire-and-forget so call sites
  // can keep passing it straight to `.catch()`.
  const showError = React.useCallback((e: unknown) => {
    void errorMessage(e).then(setMessage)
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
