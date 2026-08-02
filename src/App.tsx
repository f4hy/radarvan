import React from "react"
import "./App.css"
import Menu from "./Menu"
import { ThemeProvider } from "@mui/material/styles"
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider"
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs"
import theme from "./theme"
import { AuthProvider } from "./AuthContext"
import { PlayerColorsProvider } from "./PlayerColorsContext"

function App() {
  return (
    <div className="App">
      <ThemeProvider theme={theme}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <AuthProvider>
            <PlayerColorsProvider>
              <Menu />
            </PlayerColorsProvider>
          </AuthProvider>
        </LocalizationProvider>
      </ThemeProvider>
    </div>
  )
}

export default App
