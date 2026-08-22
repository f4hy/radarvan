
# DurationDistribution

The histogram, its summary stats, and the same stats per game format.  ``by_format`` is computed over whatever corpus reached the route, so it collapses to a single entry when the caller passed ``game_format``.

## Properties

Name | Type
------------ | -------------
`bucketMinutes` | number
`buckets` | [Array&lt;DurationBucket&gt;](DurationBucket.md)
`stats` | [DurationStats](DurationStats.md)
`byFormat` | [{ [key: string]: DurationStats; }](DurationStats.md)

## Example

```typescript
import type { DurationDistribution } from ''

// TODO: Update the object below with actual values
const example = {
  "bucketMinutes": null,
  "buckets": null,
  "stats": null,
  "byFormat": null,
} satisfies DurationDistribution

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DurationDistribution
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


