import React from "react"
import "./App.css"
import Menu from "./Menu"
import { ThemeProvider } from "@mui/material/styles"
import theme from "./theme"
import { AuthProvider } from "./AuthContext"
import { PlayerColorsProvider } from "./PlayerColorsContext"

function App() {
  return (
    <div className="App">
      <ThemeProvider theme={theme}>
        <AuthProvider>
          <PlayerColorsProvider>
            <Menu />
          </PlayerColorsProvider>
        </AuthProvider>
      </ThemeProvider>
    </div>
  )
}

export default App
