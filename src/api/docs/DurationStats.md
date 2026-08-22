
# DurationStats

Order statistics for one set of game lengths, all in minutes.

## Properties

Name | Type
------------ | -------------
`count` | number
`totalMinutes` | number
`meanMinutes` | number
`medianMinutes` | number
`p10Minutes` | number
`p90Minutes` | number
`shortestMinutes` | number
`longestMinutes` | number

## Example

```typescript
import type { DurationStats } from ''

// TODO: Update the object below with actual values
const example = {
  "count": null,
  "totalMinutes": null,
  "meanMinutes": null,
  "medianMinutes": null,
  "p10Minutes": null,
  "p90Minutes": null,
  "shortestMinutes": null,
  "longestMinutes": null,
} satisfies DurationStats

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DurationStats
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


