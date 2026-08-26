
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
`incomeBySource` | { [key: string]: { [key: string]: { [key: string]: number; }; }; }
`mapName` | string
`firstBlood` | [FirstBlood](FirstBlood.md)
`buildingFirstBlood` | [FirstBlood](FirstBlood.md)
`playerSummary` | [Array&lt;PlayerSummary&gt;](PlayerSummary.md)
`killEvents` | [Array&lt;KillEventOutput&gt;](KillEventOutput.md)
`mapEvents` | [Array&lt;MapEventOutput&gt;](MapEventOutput.md)
`playerMoneySpent` | { [key: string]: number; }
`playerMoneyCollected` | { [key: string]: number; }
`timeToRank5` | { [key: string]: number; }
`timeToSearchDestroy` | { [key: string]: number; }
`timeToHunted` | { [key: string]: number; }
`buildOrders` | [{ [key: string]: BuildOrder; }](BuildOrder.md)
`apmOverTime` | { [key: string]: { [key: string]: number; }; }
`timelineEvents` | [Array&lt;TimelineEvent&gt;](TimelineEvent.md)
`powers` | [MatchPowers](MatchPowers.md)

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
  "incomeBySource": null,
  "mapName": null,
  "firstBlood": null,
  "buildingFirstBlood": null,
  "playerSummary": null,
  "killEvents": null,
  "mapEvents": null,
  "playerMoneySpent": null,
  "playerMoneyCollected": null,
  "timeToRank5": null,
  "timeToSearchDestroy": null,
  "timeToHunted": null,
  "buildOrders": null,
  "apmOverTime": null,
  "timelineEvents": null,
  "powers": null,
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


