
# MatchNarrative

A match retold as an ordered list of beats.  ``beats`` is empty when the match has no parsed details yet; ``headline`` and the match metadata are still populated from the match row, so the UI always has something to show.

## Properties

Name | Type
------------ | -------------
`matchId` | number
`headline` | string
`beats` | [Array&lt;NarrativeBeat&gt;](NarrativeBeat.md)
`startedAt` | Date
`tournament` | string

## Example

```typescript
import type { MatchNarrative } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "headline": null,
  "beats": null,
  "startedAt": null,
  "tournament": null,
} satisfies MatchNarrative

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MatchNarrative
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


