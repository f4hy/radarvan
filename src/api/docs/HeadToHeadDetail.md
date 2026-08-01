
# HeadToHeadDetail

Detailed head-to-head record between two players in opposite-team games, plus how often they\'ve been teammates instead.

## Properties

Name | Type
------------ | -------------
`player1` | string
`player2` | string
`player1Wins` | number
`player2Wins` | number
`games` | [Array&lt;HeadToHeadGame&gt;](HeadToHeadGame.md)
`player1ByGeneral` | [Array&lt;HeadToHeadGeneralRecord&gt;](HeadToHeadGeneralRecord.md)
`player2ByGeneral` | [Array&lt;HeadToHeadGeneralRecord&gt;](HeadToHeadGeneralRecord.md)
`byMap` | [Array&lt;HeadToHeadMapRecord&gt;](HeadToHeadMapRecord.md)
`player1ValueDestroyed` | number
`player2ValueDestroyed` | number
`teammateGames` | number
`teammateWins` | number

## Example

```typescript
import type { HeadToHeadDetail } from ''

// TODO: Update the object below with actual values
const example = {
  "player1": null,
  "player2": null,
  "player1Wins": null,
  "player2Wins": null,
  "games": null,
  "player1ByGeneral": null,
  "player2ByGeneral": null,
  "byMap": null,
  "player1ValueDestroyed": null,
  "player2ValueDestroyed": null,
  "teammateGames": null,
  "teammateWins": null,
} satisfies HeadToHeadDetail

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HeadToHeadDetail
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


