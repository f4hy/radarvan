import React from "react"
import "./App.css"
import Menu from "./Menu"
import { ThemeProvider } from "@mui/material/styles"
import theme from "./theme"
import { AuthProvider } from "./AuthContext"

function App() {
  return (
    <div className="App">
      <ThemeProvider theme={theme}>
        <AuthProvider>
          <Menu />
        </AuthProvider>
      </ThemeProvider>
    </div>
  )
}

export default App
