
# ObjectUsageStat

One object\'s per-game usage rate for a player against the peer distribution - every other profiled player who played the same general.  Unlike ``FavoriteObject`` (top signature picks only), this covers every unit/building/upgrade the player has enough games to compare, so ``z_score`` can be small or negative - it\'s a browsable reference, not a highlight reel. ``peer_stddev_per_game`` is the population stddev across those peers; ``z_score`` is None when it\'s 0 (every peer had the identical rate).

## Properties

Name | Type
------------ | -------------
`name` | string
`general` | [General](General.md)
`category` | string
`perGame` | number
`peerMeanPerGame` | number
`peerMedianPerGame` | number
`peerStddevPerGame` | number
`zScore` | number
`gamesOnGeneral` | number
`peerCount` | number

## Example

```typescript
import type { ObjectUsageStat } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "general": null,
  "category": null,
  "perGame": null,
  "peerMeanPerGame": null,
  "peerMedianPerGame": null,
  "peerStddevPerGame": null,
  "zScore": null,
  "gamesOnGeneral": null,
  "peerCount": null,
} satisfies ObjectUsageStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ObjectUsageStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


