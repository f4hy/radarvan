
# FavoriteObject

A peer-normalized signature (or avoided) object for a player.  Rates are per-game on the general the object was scored against; ``score`` is the smoothed ratio player_rate/peer_rate (>1 = builds it more than peers playing the same general).

## Properties

Name | Type
------------ | -------------
`name` | string
`general` | [General](General.md)
`perGame` | number
`peerPerGame` | number
`score` | number
`gamesOnGeneral` | number
`totalCount` | number

## Example

```typescript
import type { FavoriteObject } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "general": null,
  "perGame": null,
  "peerPerGame": null,
  "score": null,
  "gamesOnGeneral": null,
  "totalCount": null,
} satisfies FavoriteObject

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FavoriteObject
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


