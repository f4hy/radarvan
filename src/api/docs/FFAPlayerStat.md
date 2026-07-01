
# FFAPlayerStat

Per-player record across free-for-all games.

## Properties

Name | Type
------------ | -------------
`name` | string
`games` | number
`wins` | number
`winRate` | number
`expectedWins` | number
`dominance` | number

## Example

```typescript
import type { FFAPlayerStat } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "games": null,
  "wins": null,
  "winRate": null,
  "expectedWins": null,
  "dominance": null,
} satisfies FFAPlayerStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FFAPlayerStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


