
# UnitDamageStat

A player\'s own highest per-game value-destroyed rate for one unit on one general - their own best, not peer-normalized (see FavoriteObject / PlayerProfileComputed.signature_damage_dealer for the peer-relative pick). \"Value destroyed\" is build cost of everything killed with this unit - the damage-dealt proxy, since replays don\'t carry raw HP.

## Properties

Name | Type
------------ | -------------
`name` | string
`general` | [General](General.md)
`perGame` | number
`totalValueDestroyed` | number
`killCount` | number
`gamesOnGeneral` | number

## Example

```typescript
import type { UnitDamageStat } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "general": null,
  "perGame": null,
  "totalValueDestroyed": null,
  "killCount": null,
  "gamesOnGeneral": null,
} satisfies UnitDamageStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UnitDamageStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


