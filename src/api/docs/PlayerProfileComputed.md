
# PlayerProfileComputed

MatchDetails-derived deep stats for one player.  Computed as a batch across all profiled players (percentiles are relative to that population) and persisted per player; see radarvan.player_profile.

## Properties

Name | Type
------------ | -------------
`favoriteUnit` | [FavoriteObject](FavoriteObject.md)
`favoriteBuilding` | [FavoriteObject](FavoriteObject.md)
`favoriteUpgrade` | [FavoriteObject](FavoriteObject.md)
`favoritePower` | [FavoriteObject](FavoriteObject.md)
`aversions` | [Array&lt;FavoriteObject&gt;](FavoriteObject.md)
`avgApm` | number
`apmPercentile` | number
`firstBloodRate` | number
`firstBloodPercentile` | number
`avgTimeToRank5` | number
`rank5Percentile` | number
`superweaponsBuiltPerGame` | number
`superweaponPercentile` | number
`badges` | [Array&lt;ProfileBadge&gt;](ProfileBadge.md)
`objectUsage` | [Array&lt;ObjectUsageStat&gt;](ObjectUsageStat.md)
`gamesAnalyzed` | number
`computedAt` | Date

## Example

```typescript
import type { PlayerProfileComputed } from ''

// TODO: Update the object below with actual values
const example = {
  "favoriteUnit": null,
  "favoriteBuilding": null,
  "favoriteUpgrade": null,
  "favoritePower": null,
  "aversions": null,
  "avgApm": null,
  "apmPercentile": null,
  "firstBloodRate": null,
  "firstBloodPercentile": null,
  "avgTimeToRank5": null,
  "rank5Percentile": null,
  "superweaponsBuiltPerGame": null,
  "superweaponPercentile": null,
  "badges": null,
  "objectUsage": null,
  "gamesAnalyzed": null,
  "computedAt": null,
} satisfies PlayerProfileComputed

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerProfileComputed
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


