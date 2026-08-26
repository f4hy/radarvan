
# PowerRow

One power, for one player, on one general - against the group baseline.  The baseline is every *other* player on the same general, not the whole group including this player. With a roster this small, leaving someone in their own comparison flattens exactly the signal the row exists to show.

## Properties

Name | Type
------------ | -------------
`power` | string
`purchasable` | boolean
`unlocksUnit` | boolean
`gamesPicked` | number
`pickRate` | number
`groupPickRate` | number
`avgPickMinute` | number
`groupAvgPickMinute` | number
`avgLevels` | number
`groupAvgLevels` | number
`uses` | number
`usesPerMinute` | number
`groupUsesPerMinute` | number

## Example

```typescript
import type { PowerRow } from ''

// TODO: Update the object below with actual values
const example = {
  "power": null,
  "purchasable": null,
  "unlocksUnit": null,
  "gamesPicked": null,
  "pickRate": null,
  "groupPickRate": null,
  "avgPickMinute": null,
  "groupAvgPickMinute": null,
  "avgLevels": null,
  "groupAvgLevels": null,
  "uses": null,
  "usesPerMinute": null,
  "groupUsesPerMinute": null,
} satisfies PowerRow

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PowerRow
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


