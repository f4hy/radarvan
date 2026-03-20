
# MatchDetails


## Properties

Name | Type
------------ | -------------
`matchId` | number
`gameVersion` | string
`costs` | [Array&lt;Costs&gt;](Costs.md)
`apms` | [Array&lt;APM&gt;](APM.md)
`upgradeEvents` | [{ [key: string]: Upgrades; }](Upgrades.md)
`statsData` | { [key: string]: { [key: string]: { [key: string]: number; }; }; }
`mapName` | string
`firstBlood` | [FirstBlood](FirstBlood.md)
`buildingFirstBlood` | [FirstBlood](FirstBlood.md)
`playerSummary` | [Array&lt;PlayerSummary&gt;](PlayerSummary.md)
`killEvents` | [Array&lt;KillEventOutput&gt;](KillEventOutput.md)

## Example

```typescript
import type { MatchDetails } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "gameVersion": null,
  "costs": null,
  "apms": null,
  "upgradeEvents": null,
  "statsData": null,
  "mapName": null,
  "firstBlood": null,
  "buildingFirstBlood": null,
  "playerSummary": null,
  "killEvents": null,
} satisfies MatchDetails

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MatchDetails
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


