
# MatchPrediction

Win prediction from the N-model ONNX ensemble.  Teams are labelled A/B by ascending team id (the model\'s canonical ordering); ``prob_team_a_wins`` is the mean calibrated probability that team A wins across the ensemble. ``prob_team_a_wins_std`` is the spread across replicates (see ``ml.bootstrap_matrix``) - a large value means the ensemble disagrees with itself and this prediction shouldn\'t be trusted much, which matters given how little training data there is.

## Properties

Name | Type
------------ | -------------
`matchId` | number
`mapName` | string
`teamA` | number
`teamB` | number
`teamAPlayers` | Array&lt;string&gt;
`teamBPlayers` | Array&lt;string&gt;
`probTeamAWins` | number
`probTeamAWinsStd` | number
`ensembleSize` | number
`favoredTeam` | number
`favoredWinProb` | number
`unknownPlayers` | Array&lt;string&gt;

## Example

```typescript
import type { MatchPrediction } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "mapName": null,
  "teamA": null,
  "teamB": null,
  "teamAPlayers": null,
  "teamBPlayers": null,
  "probTeamAWins": null,
  "probTeamAWinsStd": null,
  "ensembleSize": null,
  "favoredTeam": null,
  "favoredWinProb": null,
  "unknownPlayers": null,
} satisfies MatchPrediction

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MatchPrediction
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


