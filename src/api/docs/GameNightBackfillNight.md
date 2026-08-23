
# GameNightBackfillNight

What the backfill did about one night in the window, and why.  Every night considered gets a row, including the ones left alone - the point of the report is to show what a run *would* have spent on, so the operator can widen the budget deliberately rather than by rerunning blind.

## Properties

Name | Type
------------ | -------------
`date` | Date
`matches` | number
`outcome` | string

## Example

```typescript
import type { GameNightBackfillNight } from ''

// TODO: Update the object below with actual values
const example = {
  "date": null,
  "matches": null,
  "outcome": null,
} satisfies GameNightBackfillNight

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameNightBackfillNight
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


