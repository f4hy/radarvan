import * as React from "react"
import { EASE, REDUCED_MOTION } from "./motion"

interface IndicatorRect {
  top: number
  left: number
  width: number
  height: number
  /** False for the first placement, so the indicator appears instead of flying in. */
  animate: boolean
}

// Tracks the element matching `selector` inside the returned ref's container,
// which must be positioned (offsets are relative to it). `key` is whatever
// changing means the match may have moved.
export function useSlidingIndicator<T extends HTMLElement>(
  selector: string,
  key: unknown,
) {
  const ref = React.useRef<T>(null)
  const [rect, setRect] = React.useState<IndicatorRect | null>(null)

  const measure = React.useCallback(() => {
    const container = ref.current
    // display:none (the other breakpoint's drawer) measures as all zeros.
    if (!container || container.getClientRects().length === 0) return
    const target = container.querySelector<HTMLElement>(selector)
    if (!target) {
      setRect(null)
      return
    }
    const next = {
      top: target.offsetTop,
      left: target.offsetLeft,
      width: target.offsetWidth,
      height: target.offsetHeight,
    }
    setRect((prev) =>
      prev &&
      prev.top === next.top &&
      prev.left === next.left &&
      prev.width === next.width &&
      prev.height === next.height
        ? prev
        : { ...next, animate: prev !== null },
    )
  }, [selector])

  React.useLayoutEffect(measure, [key, measure])

  // Layout can move the target without `key` changing.
  React.useEffect(() => {
    const container = ref.current
    if (!container) return
    const observer = new ResizeObserver(measure)
    observer.observe(container)
    return () => observer.disconnect()
  }, [measure])

  return { ref, rect }
}

export function indicatorSx(rect: IndicatorRect | null) {
  return {
    position: "absolute",
    top: 0,
    left: 0,
    width: rect?.width ?? 0,
    height: rect?.height ?? 0,
    transform: `translate(${rect?.left ?? 0}px, ${rect?.top ?? 0}px)`,
    opacity: rect ? 1 : 0,
    pointerEvents: "none",
    transition: rect?.animate
      ? `transform 280ms ${EASE}, width 280ms ${EASE}, height 280ms ${EASE}, opacity 150ms`
      : "none",
    [REDUCED_MOTION]: { transition: "none" },
  } as const
}
