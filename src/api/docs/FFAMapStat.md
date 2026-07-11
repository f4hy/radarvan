
# FFAMapStat

Per-map activity across free-for-all games.

## Properties

Name | Type
------------ | -------------
`map` | string
`games` | number
`avgPlayers` | number

## Example

```typescript
import type { FFAMapStat } from ''

// TODO: Update the object below with actual values
const example = {
  "map": null,
  "games": null,
  "avgPlayers": null,
} satisfies FFAMapStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FFAMapStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


