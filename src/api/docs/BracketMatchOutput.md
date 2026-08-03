
# BracketMatchOutput


## Properties

Name | Type
------------ | -------------
`matchId` | string
`bracket` | string
`roundNumber` | number
`roundName` | string
`playerA` | string
`playerB` | string
`scheduledAt` | Date
`bestOf` | number
`scoreA` | number
`scoreB` | number
`winner` | string
`status` | string
`sourceA` | [SourceA](SourceA.md)
`sourceB` | [SourceB](SourceB.md)

## Example

```typescript
import type { BracketMatchOutput } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "bracket": null,
  "roundNumber": null,
  "roundName": null,
  "playerA": null,
  "playerB": null,
  "scheduledAt": null,
  "bestOf": null,
  "scoreA": null,
  "scoreB": null,
  "winner": null,
  "status": null,
  "sourceA": null,
  "sourceB": null,
} satisfies BracketMatchOutput

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BracketMatchOutput
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


