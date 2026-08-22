
# GameNightRecap

Everything the recap page shows for one game night.  ``match_count`` counts every match played that night; ``counted_matches`` is the decided-competitive subset the player lines and most highlights are computed over. The two differ when the night included comp-stomps, unfinished games, or games with an unknown player.

## Properties

Name | Type
------------ | -------------
`date` | Date
`matchCount` | number
`countedMatches` | number
`totalMinutes` | number
`medianMinutes` | number
`startedAt` | Date
`endedAt` | Date
`formats` | { [key: string]: number; }
`maps` | { [key: string]: number; }
`players` | [Array&lt;GameNightPlayerLine&gt;](GameNightPlayerLine.md)
`highlights` | [Array&lt;GameNightHighlight&gt;](GameNightHighlight.md)
`aiSummary` | string
`aiSummaryProvider` | string
`aiSummaryComputedAt` | Date

## Example

```typescript
import type { GameNightRecap } from ''

// TODO: Update the object below with actual values
const example = {
  "date": null,
  "matchCount": null,
  "countedMatches": null,
  "totalMinutes": null,
  "medianMinutes": null,
  "startedAt": null,
  "endedAt": null,
  "formats": null,
  "maps": null,
  "players": null,
  "highlights": null,
  "aiSummary": null,
  "aiSummaryProvider": null,
  "aiSummaryComputedAt": null,
} satisfies GameNightRecap

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameNightRecap
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


