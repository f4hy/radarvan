import { keyframes, type Theme } from "@mui/material/styles"

export const EASE = "cubic-bezier(0.2, 0, 0, 1)"
export const REDUCED_MOTION = "@media (prefers-reduced-motion: reduce)"

const fadeIn = keyframes`
  from { opacity: 0; }
  to { opacity: 1; }
`
const riseIn = keyframes`
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: none; }
`
// No `to`: each bar animates up to whatever size its own styles give it.
const growX = keyframes`
  from { transform: scaleX(0); }
`
const slideInX = keyframes`
  from { transform: translateX(-100%); }
`

export const fadeInSx = {
  animation: `${fadeIn} 220ms ease-out`,
  [REDUCED_MOTION]: { animation: "none" },
} as const

// The shell's route-enter; pages don't add their own.
export const pageEnterSx = {
  animation: `${riseIn} 180ms ease-out`,
  [REDUCED_MOTION]: { animation: "none" },
} as const

const STAGGER_STEP_MS = 30
// Past this many items the tail of a long list would still be arriving a
// second after the page did.
export const STAGGER_CAP = 12

// `backwards`, not `both`: a forwards fill would pin `transform` after the
// animation and silently beat any hover transform on the same element.
const STAGGER_SX = Array.from({ length: STAGGER_CAP + 1 }, (_, step) => ({
  animation: `${riseIn} 320ms ${EASE} backwards`,
  animationDelay: `${step * STAGGER_STEP_MS}ms`,
  [REDUCED_MOTION]: { animation: "none" },
}))

export function staggerSx(index: number) {
  return STAGGER_SX[Math.min(index, STAGGER_CAP)]
}

export const growInSx = {
  transformOrigin: "left",
  animation: `${growX} 600ms ${EASE} backwards`,
  [REDUCED_MOTION]: { animation: "none" },
} as const

export const slideInSx = {
  animation: `${slideInX} 600ms ${EASE} backwards`,
  [REDUCED_MOTION]: { animation: "none" },
} as const

const HOVER_TRANSITION = `transform 180ms ${EASE}, box-shadow 180ms ${EASE}, border-color 180ms ${EASE}`

export function hoverShadowSx(t: Theme) {
  return {
    transition: HOVER_TRANSITION,
    "&:hover": { boxShadow: "0 6px 18px rgba(16, 24, 40, 0.10)" },
    ...t.applyStyles("dark", {
      "&:hover": { boxShadow: "0 6px 18px rgba(0, 0, 0, 0.45)" },
    }),
    [REDUCED_MOTION]: { transition: "none" },
  }
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia(REDUCED_MOTION.replace("@media ", "")).matches
}
