
# FFAGeneralStat

Per-general win record across free-for-all games.

## Properties

Name | Type
------------ | -------------
`general` | [General](General.md)
`games` | number
`wins` | number
`winRate` | number

## Example

```typescript
import type { FFAGeneralStat } from ''

// TODO: Update the object below with actual values
const example = {
  "general": null,
  "games": null,
  "wins": null,
  "winRate": null,
} satisfies FFAGeneralStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FFAGeneralStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


