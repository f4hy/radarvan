
# WinProbOverTime

Win-probability-over-time for one match (sequence ONNX model).  ``points`` is ordered by time; ``prob_team_a`` is P(team A wins) given the game up to that window. Team A is the lower team id (the model\'s canonical ordering).

## Properties

Name | Type
------------ | -------------
`matchId` | number
`teamAPlayers` | Array&lt;string&gt;
`teamBPlayers` | Array&lt;string&gt;
`actualWinner` | string
`points` | [Array&lt;WinProbPoint&gt;](WinProbPoint.md)

## Example

```typescript
import type { WinProbOverTime } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "teamAPlayers": null,
  "teamBPlayers": null,
  "actualWinner": null,
  "points": null,
} satisfies WinProbOverTime

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as WinProbOverTime
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


