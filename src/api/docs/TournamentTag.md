
# TournamentTag

The tournament a match counted toward, if any.  Denormalized onto MatchInfo from the ``tournament_games`` link so callers can tell tournament games apart without a second query. ``stage`` is the bracket match id (\"WB2-2\") and is None for round-robin games. Identity only - the display name lives on the tournament (``/api/tournaments``) rather than being copied onto every match of every listing.

## Properties

Name | Type
------------ | -------------
`slug` | string
`stage` | string
`roundName` | string
`seriesIndex` | number

## Example

```typescript
import type { TournamentTag } from ''

// TODO: Update the object below with actual values
const example = {
  "slug": null,
  "stage": null,
  "roundName": null,
  "seriesIndex": null,
} satisfies TournamentTag

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TournamentTag
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


