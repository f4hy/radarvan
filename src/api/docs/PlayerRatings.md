
# PlayerRatings


## Properties

Name | Type
------------ | -------------
`name` | string
`ordinal` | number
`mu` | number
`sigma` | number
`gameCount` | number
`atdate` | Date
`recentDelta` | number
`delta7d` | number
`delta30d` | number
`highOrdinal` | number
`lowOrdinal` | number

## Example

```typescript
import type { PlayerRatings } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "ordinal": null,
  "mu": null,
  "sigma": null,
  "gameCount": null,
  "atdate": null,
  "recentDelta": null,
  "delta7d": null,
  "delta30d": null,
  "highOrdinal": null,
  "lowOrdinal": null,
} satisfies PlayerRatings

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerRatings
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


