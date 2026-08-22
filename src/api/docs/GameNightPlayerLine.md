
# GameNightPlayerLine

One player\'s night: their record and what they played.  Computed over the night\'s *decided competitive* games only, so it agrees with every other W/L surface in the app (see the \"two match sets\" note in CLAUDE.md). Observers never appear - a spectator slot is not a game played.

## Properties

Name | Type
------------ | -------------
`player` | string
`wins` | number
`losses` | number
`games` | number
`generals` | Array&lt;string&gt;
`bestStreak` | number
`bestApm` | number

## Example

```typescript
import type { GameNightPlayerLine } from ''

// TODO: Update the object below with actual values
const example = {
  "player": null,
  "wins": null,
  "losses": null,
  "games": null,
  "generals": null,
  "bestStreak": null,
  "bestApm": null,
} satisfies GameNightPlayerLine

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameNightPlayerLine
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


