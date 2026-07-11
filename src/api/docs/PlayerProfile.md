
# PlayerProfile

Full profile for one player: live MatchInfo-derived stats plus the persisted deep stats (None until the batch recompute has run).

## Properties

Name | Type
------------ | -------------
`player` | string
`games` | number
`wins` | number
`losses` | number
`generals` | [Array&lt;GeneralProfileStat&gt;](GeneralProfileStat.md)
`generalWinRateOverTime` | [Array&lt;GeneralWinRateSeries&gt;](GeneralWinRateSeries.md)
`mostPlayedGeneral` | [GeneralProfileStat](GeneralProfileStat.md)
`bestGeneral` | [GeneralProfileStat](GeneralProfileStat.md)
`favoriteMap` | [MapProfileStat](MapProfileStat.md)
`bestMap` | [MapProfileStat](MapProfileStat.md)
`favoriteTeammate` | [TeammateProfileStat](TeammateProfileStat.md)
`nemesis` | [OpponentProfileStat](OpponentProfileStat.md)
`favoriteVictim` | [OpponentProfileStat](OpponentProfileStat.md)
`avgWinDurationMinutes` | number
`avgLossDurationMinutes` | number
`computed` | [PlayerProfileComputed](PlayerProfileComputed.md)

## Example

```typescript
import type { PlayerProfile } from ''

// TODO: Update the object below with actual values
const example = {
  "player": null,
  "games": null,
  "wins": null,
  "losses": null,
  "generals": null,
  "generalWinRateOverTime": null,
  "mostPlayedGeneral": null,
  "bestGeneral": null,
  "favoriteMap": null,
  "bestMap": null,
  "favoriteTeammate": null,
  "nemesis": null,
  "favoriteVictim": null,
  "avgWinDurationMinutes": null,
  "avgLossDurationMinutes": null,
  "computed": null,
} satisfies PlayerProfile

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerProfile
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


