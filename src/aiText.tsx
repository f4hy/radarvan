// biome-ignore-all lint/suspicious/noArrayIndexKey: these render the split
// of one immutable string in place. The chunks never reorder, are never
// inserted into, and hold no state — position IS the identity here.
import Typography from "@mui/material/Typography"
import * as React from "react"

/**
 * Rendering for the LLM-written blurbs (bracket hype, post-game recap, game
 * night recap) and the tournament rules list.
 *
 * The prompt guidelines all impose the same output shape — plain paragraphs
 * separated by blank lines, with inline `**bold**` and nothing else — so this
 * tiny renderer covers every one of them and no markdown dependency is needed.
 * Anything richer arriving from the model is a prompt bug, not a renderer gap.
 */

// Splits on **bold** markers into <strong> spans.
export function renderBoldSegments(text: string): React.ReactNode {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .map((chunk, i) =>
      chunk.startsWith("**") && chunk.endsWith("**") ? (
        <strong key={i}>{chunk.slice(2, -2)}</strong>
      ) : (
        <React.Fragment key={i}>{chunk}</React.Fragment>
      ),
    )
}

// Blank-line separated paragraphs with inline emphasis.
export function renderAiText(text: string): React.ReactNode {
  const paragraphs = text.split("\n\n").filter((p) => p.trim().length > 0)
  return paragraphs.map((paragraph, pIdx) => (
    <Typography
      key={pIdx}
      variant="body2"
      sx={{ mb: pIdx === paragraphs.length - 1 ? 0 : 1 }}
    >
      {renderBoldSegments(paragraph)}
    </Typography>
  ))
}
