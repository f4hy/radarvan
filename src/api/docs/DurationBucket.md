
# DurationBucket

One histogram bar: games whose duration is in [start, end) minutes.  The final bucket is the overflow bin and is half-open the other way - ``end_minutes`` is null and it holds everything at or beyond ``start``, so one four-hour marathon widens the tail label instead of the whole axis.

## Properties

Name | Type
------------ | -------------
`startMinutes` | number
`endMinutes` | number
`count` | number

## Example

```typescript
import type { DurationBucket } from ''

// TODO: Update the object below with actual values
const example = {
  "startMinutes": null,
  "endMinutes": null,
  "count": null,
} satisfies DurationBucket

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DurationBucket
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


