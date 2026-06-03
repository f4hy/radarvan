import React from "react"
import "./App.css"
import Menu from "./Menu"
import { ThemeProvider } from "@mui/material/styles"
import theme from "./theme"

function App() {
  return (
    <div className="App">
      <ThemeProvider theme={theme}>
        <Menu />
      </ThemeProvider>
    </div>
  )
}

export default App
