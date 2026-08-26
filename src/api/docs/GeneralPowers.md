
# GeneralPowers

One player\'s power habits on one general.

## Properties

Name | Type
------------ | -------------
`general` | [General](General.md)
`games` | number
`minutes` | number
`groupGames` | number
`reconPerMinute` | number
`groupReconPerMinute` | number
`rows` | [Array&lt;PowerRow&gt;](PowerRow.md)

## Example

```typescript
import type { GeneralPowers } from ''

// TODO: Update the object below with actual values
const example = {
  "general": null,
  "games": null,
  "minutes": null,
  "groupGames": null,
  "reconPerMinute": null,
  "groupReconPerMinute": null,
  "rows": null,
} satisfies GeneralPowers

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GeneralPowers
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


