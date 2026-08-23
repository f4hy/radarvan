
# GameNightBackfill

The result of one backfill run over the last N game nights.

## Properties

Name | Type
------------ | -------------
`days` | number
`generated` | number
`remaining` | number
`nights` | [Array&lt;GameNightBackfillNight&gt;](GameNightBackfillNight.md)

## Example

```typescript
import type { GameNightBackfill } from ''

// TODO: Update the object below with actual values
const example = {
  "days": null,
  "generated": null,
  "remaining": null,
  "nights": null,
} satisfies GameNightBackfill

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameNightBackfill
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


