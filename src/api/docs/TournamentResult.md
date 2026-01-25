
# TournamentResult


## Properties

Name | Type
------------ | -------------
`tournament` | [Tournament](Tournament.md)
`matchups` | [Array&lt;MatchupResult&gt;](MatchupResult.md)
`records` | [{ [key: string]: WinLoss; }](WinLoss.md)
`complete` | boolean

## Example

```typescript
import type { TournamentResult } from ''

// TODO: Update the object below with actual values
const example = {
  "tournament": null,
  "matchups": null,
  "records": null,
  "complete": null,
} satisfies TournamentResult

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TournamentResult
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


