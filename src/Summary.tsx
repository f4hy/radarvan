import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import DownloadIcon from "@mui/icons-material/Download"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ThumbDownIcon from "@mui/icons-material/ThumbDown"
import Button from "@mui/material/Button"
import Card from "@mui/material/Card"
import CardHeader from "@mui/material/CardHeader"
import CardContent from "@mui/material/CardContent"
import Grid from "@mui/material/Grid"
import Stack from "@mui/material/Stack"
import Divider from "@mui/material/Divider"
import ListItem from "@mui/material/ListItem"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import { blue, lightGreen, purple, red } from "@mui/material/colors"
import Container from "@mui/material/Container"
import _ from "lodash"
import * as React from "react"
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { MatchDetails, Spent, Upgrades, APM, PlayerSummary } from "./api"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"


export default function ShowPlayerSummary(props: { playerSummary: PlayerSummary }) {
  return (
    <Accordion>
      <AccordionSummary>
        <Typography>{props.playerSummary.name + " Details"}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Typography>Money Spent{props.playerSummary.moneySpent}</Typography>
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        {Object.entries(props.playerSummary.unitsCreated).map(([name, obj]) => {
          return <Typography>{"Units Created: " + name + " " + obj.count}</Typography>
        }
        )}
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        {Object.entries(props.playerSummary.buildingsBuilt).map(([name, obj]) => {
          return <Typography>{"Buildings Built: " + name + " " + obj.count}</Typography>
        }
        )}
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        {Object.entries(props.playerSummary.upgradesBuilt).map(([name, obj]) => {
          return <Typography>{"Upgrades: " + name + " " + obj.count}</Typography>
        }
        )}
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        {Object.entries(props.playerSummary.powersUsed).map(([name, count]) => {
          return <Typography>{"Powers Used: " + name + " " + count}</Typography>
        }
        )}
      </AccordionDetails>

    </Accordion>
  )
}
