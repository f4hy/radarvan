
# BracketSummaryResponse

The AI-generated post-game recap of one completed bracket set.  ``summary`` is null while the set isn\'t recappable yet - not finished, or finished but with fewer replays linked than games played. ``ready`` says which of those it is, so the UI can promise a recap that\'s coming instead of showing nothing.

## Properties

Name | Type
------------ | -------------
`matchId` | string
`ready` | boolean
`summary` | string

## Example

```typescript
import type { BracketSummaryResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "ready": null,
  "summary": null,
} satisfies BracketSummaryResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BracketSummaryResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


