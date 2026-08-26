
# UnusualPick

A pick rate that stands out from the rest of the group.  `surprise` is the gap in pick rate scaled by how much evidence there is for it - a binomial z-score against the group\'s rate. It exists so one game of something odd doesn\'t outrank a habit held over thirty.

## Properties

Name | Type
------------ | -------------
`general` | [General](General.md)
`power` | string
`games` | number
`pickRate` | number
`groupPickRate` | number
`surprise` | number
`direction` | string

## Example

```typescript
import type { UnusualPick } from ''

// TODO: Update the object below with actual values
const example = {
  "general": null,
  "power": null,
  "games": null,
  "pickRate": null,
  "groupPickRate": null,
  "surprise": null,
  "direction": null,
} satisfies UnusualPick

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UnusualPick
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


