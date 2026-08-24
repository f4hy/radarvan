import Box from "@mui/material/Box"
import Grid from "@mui/material/Grid"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { ActivityCalendar } from "react-activity-calendar"
import { BRAND_COLOR } from "./theme"

/**
 * A year-by-year heatmap of how much we played, one cell per game night.
 *
 * This lived on the Matches page, where clicking a cell scrolled that day's
 * accordion into view. It is really a date picker, so it belongs to the page
 * that shows one night — clicking a cell there just selects that night, and
 * the component no longer needs to know anything about scrolling or refs.
 */

function groupByYear(
  dateCounts: Record<string, number>,
): Record<string, Record<string, number>> {
  const years: Record<string, Record<string, number>> = {}
  for (const [date, count] of Object.entries(dateCounts)) {
    const year = date.slice(0, 4)
    if (!years[year]) years[year] = {}
    years[year][date] = count
  }
  return years
}

// A past year runs to Dec 31; the current one stops today, so the grid doesn't
// trail off into months that haven't happened.
function getEndDate(date: Date): Date {
  const now = new Date()
  if (date.getUTCFullYear() === now.getUTCFullYear()) {
    return now
  }
  return new Date(Date.UTC(date.getUTCFullYear(), 11, 31))
}

function toActivityData(dateCounts: Record<string, number>) {
  // groupByYear only creates a year key once a date lands in it, so this is
  // never called with an empty map.
  const dates = Object.keys(dateCounts).sort()
  const first = dates[0]
  const yearStart = new Date(`${first.slice(0, 4)}-01-01`)
  const end = getEndDate(new Date(dates[dates.length - 1]))
  const maxCount = Math.max(...Object.values(dateCounts))

  const data = []
  // Step in UTC: the date keys come from toISOString() (UTC), and yearStart is
  // UTC midnight, so advancing by local days would let a DST shift knock every
  // subsequent key off by one in some timezones.
  for (
    let d = new Date(yearStart);
    d <= end;
    d.setUTCDate(d.getUTCDate() + 1)
  ) {
    const dateStr = d.toISOString().split("T")[0]
    const count = dateCounts[dateStr] ?? 0
    const level =
      count === 0 ? 0 : (Math.ceil((count / maxCount) * 4) as 0 | 1 | 2 | 3 | 4)
    data.push({ date: dateStr, count, level })
  }

  return data
}

export default function MatchActivityCalendar(props: {
  /** Game-night date key ("YYYY-MM-DD") to number of games played. */
  dateCounts: Record<string, number>
  onSelect: (date: string) => void
  /** The night currently being shown, ringed so it's findable in the grid. */
  selected?: string | null
}) {
  const { onSelect, selected } = props
  // Newest year first, matching every other listing in the app.
  const years = React.useMemo(
    () =>
      Object.entries(groupByYear(props.dateCounts))
        .sort(([a], [b]) => b.localeCompare(a))
        .map(([year, counts]) => ({ year, data: toActivityData(counts) })),
    [props.dateCounts],
  )

  const renderBlock = React.useCallback(
    (block: React.ReactElement, activity: { date: string; count: number }) => {
      const playable = activity.count > 0
      const isSelected = activity.date === selected
      return (
        // stroke/stroke-width are inherited SVG presentation attributes, so
        // ringing the selected night is a property of this wrapper rather than
        // a cloned copy of the library's own block element.
        <g
          onClick={playable ? () => onSelect(activity.date) : undefined}
          style={{ cursor: playable ? "pointer" : "default" }}
          stroke={isSelected ? BRAND_COLOR : undefined}
          strokeWidth={isSelected ? 2 : undefined}
        >
          {block}
        </g>
      )
    },
    [onSelect, selected],
  )

  return (
    <Grid container spacing={2}>
      {years.map(({ year, data }, idx) => (
        <Grid key={year} size={{ xs: 12, lg: 6 }}>
          <Box sx={{ overflowX: "auto", pb: 1 }}>
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
              {year}
            </Typography>
            <ActivityCalendar
              data={data}
              weekStart={1}
              showWeekdayLabels={["wed", "sat"]}
              blockSize={10}
              blockMargin={4}
              showColorLegend={idx === 0}
              labels={{ totalCount: "{{count}} games in {{year}}" }}
              colorScheme="light"
              theme={{
                light: ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
              }}
              tooltips={{
                activity: {
                  text: (activity) =>
                    activity.count > 0
                      ? `${activity.count} games on ${activity.date}. Click to open.`
                      : `Nothing played on ${activity.date}`,
                  placement: "bottom",
                  offset: 6,
                  hoverRestMs: 10,
                  transitionStyles: {
                    duration: 50,
                    common: { fontFamily: "monospace" },
                  },
                  withArrow: true,
                },
              }}
              renderBlock={renderBlock}
            />
          </Box>
        </Grid>
      ))}
    </Grid>
  )
}
