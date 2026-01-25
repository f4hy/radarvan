
# MatchupResult


## Properties

Name | Type
------------ | -------------
`tournamentName` | string
`matches` | [Array&lt;MatchInfo&gt;](MatchInfo.md)
`outcome` | [{ [key: string]: WinLoss; }](WinLoss.md)
`override` | string

## Example

```typescript
import type { MatchupResult } from ''

// TODO: Update the object below with actual values
const example = {
  "tournamentName": null,
  "matches": null,
  "outcome": null,
  "override": null,
} satisfies MatchupResult

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MatchupResult
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


