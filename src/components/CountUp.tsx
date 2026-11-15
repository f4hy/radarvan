import * as React from "react"
import { prefersReducedMotion } from "../lib/motion"

const DURATION_MS = 700

interface NumericText {
  prefix: string
  target: number
  suffix: string
  decimals: number
  grouped: boolean
}

// Exactly one number with nothing numeric around it: "$1,234", "97.9% to win".
// "12:34" and "3-0" are not one quantity and are left alone.
const NUMERIC = /^(\D*)(\d[\d,]*(?:\.\d+)?)(\D*)$/

export function parseNumericText(text: string): NumericText | null {
  const m = NUMERIC.exec(text)
  if (!m) return null
  const target = Number(m[2].replaceAll(",", ""))
  if (!Number.isFinite(target)) return null
  return {
    prefix: m[1],
    target,
    suffix: m[3],
    decimals: m[2].split(".")[1]?.length ?? 0,
    grouped: m[2].includes(","),
  }
}

const formatters = new Map<string, Intl.NumberFormat>()

function render(n: NumericText, value: number): string {
  const key = `${n.decimals}|${n.grouped}`
  let format = formatters.get(key)
  if (!format) {
    format = new Intl.NumberFormat("en-US", {
      minimumFractionDigits: n.decimals,
      maximumFractionDigits: n.decimals,
      useGrouping: n.grouped,
    })
    formatters.set(key, format)
  }
  return `${n.prefix}${format.format(value)}${n.suffix}`
}

/** Counts up to a headline number; text that isn't one number renders as-is. */
export default function CountUp(props: { value: string | number }) {
  const text = String(props.value)
  const parsed = React.useMemo(() => parseNumericText(text), [text])
  const from = React.useRef(0)
  const [shown, setShown] = React.useState(() =>
    parsed && !prefersReducedMotion() ? render(parsed, 0) : text,
  )

  React.useEffect(() => {
    if (!parsed || prefersReducedMotion()) {
      setShown(text)
      return
    }
    const start = performance.now()
    const origin = from.current
    let frame = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DURATION_MS)
      const eased = 1 - (1 - t) ** 3
      const value = origin + (parsed.target - origin) * eased
      from.current = value
      setShown(t < 1 ? render(parsed, value) : text)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [parsed, text])

  if (!parsed) return <>{text}</>
  // Equal-width digits so the text around the number doesn't jitter.
  return <span style={{ fontVariantNumeric: "tabular-nums" }}>{shown}</span>
}
