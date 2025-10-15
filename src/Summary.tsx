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
import { MatchDetails, Spent, Upgrades, APM, PlayerSummary, ObjectSummary } from "./api"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"


function removeUnitPrefix(s: string): string {
  return s.replace(/.*_/g, "").replace("America", "").replace("China", "").replace("GLA", "")
}

function BuiltChart(props: {
  built: { [key: string]: ObjectSummary }
  title: string
}) {
  if (Object.keys(props.built).length < 1) {
    return (<div>No data</div>)
  }
  const data = Object.entries(props.built).map(([unit, values]) => ({
    ...values,
    unit: unit,
  }))
  return (
    <>
      <Typography>{props.title}</Typography>
      <Stack direction="row">
        <ResponsiveContainer width="90%" height={300}>
          <BarChart
            title={props.title}
            height={300}
            layout="vertical"
            data={data}
            margin={{ top: 5, right: 5, left: 200, bottom: 5 }}
          >
            <YAxis dataKey="unit" type="category" tickFormatter={removeUnitPrefix}
            />
            <XAxis dataKey="count" type="number" orientation="top" allowDecimals={false}
            />
            <Tooltip />
            <Bar dataKey="count" fill="#8884d8" label={{ fill: 'black', fontSize: 20 }} />
          </BarChart>
        </ResponsiveContainer>
        <ResponsiveContainer width="80%" height={300}>
          <BarChart
            title={props.title}
            height={300}
            layout="vertical"
            data={data}
            margin={{ top: 5, right: 5, left: 20, bottom: 5 }}
          >
            <YAxis dataKey="unit" type="category" tickFormatter={removeUnitPrefix} hide={true}
            />
            <XAxis dataKey="totalSpent" type="number" name="$" orientation="top"
            />
            <Tooltip />
            <Bar dataKey="totalSpent" fill="green" />
          </BarChart>
        </ResponsiveContainer>
      </Stack>
    </>
  )
}


export default function ShowPlayerSummary(props: { playerSummary: PlayerSummary }) {
  return (
    <Accordion>
      <AccordionSummary>
        <Typography>{props.playerSummary.name + " Details"}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Typography>Money Spent: ${props.playerSummary.moneySpent}</Typography>
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        <BuiltChart title="Units Created" built={props.playerSummary.unitsCreated} />
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        <BuiltChart title="Buildings Created" built={props.playerSummary.buildingsBuilt} />
      </AccordionDetails>
      <Divider />
      <AccordionDetails>
        <BuiltChart title="Upgrades" built={props.playerSummary.upgradesBuilt} />
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
