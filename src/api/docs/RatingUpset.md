
# RatingUpset

A game where the rating model\'s favored team lost.  Win probabilities are the model\'s pre-game prediction for each team using the converged ratings; ``surprise`` is the favorite\'s edge over the actual winner.

## Properties

Name | Type
------------ | -------------
`matchId` | number
`atdate` | Date
`favoredTeam` | number
`favoredPlayers` | Array&lt;string&gt;
`favoredWinProb` | number
`winningTeam` | number
`winnerPlayers` | Array&lt;string&gt;
`winnerWinProb` | number
`surprise` | number

## Example

```typescript
import type { RatingUpset } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "atdate": null,
  "favoredTeam": null,
  "favoredPlayers": null,
  "favoredWinProb": null,
  "winningTeam": null,
  "winnerPlayers": null,
  "winnerWinProb": null,
  "surprise": null,
} satisfies RatingUpset

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as RatingUpset
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


