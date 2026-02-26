
# PlayerRatingData


## Properties

Name | Type
------------ | -------------
`playerRating` | [Array&lt;PlayerRatings&gt;](PlayerRatings.md)
`playerRatingOvertime` | { [key: string]: Array&lt;ShortPlayerRating&gt;; }

## Example

```typescript
import type { PlayerRatingData } from ''

// TODO: Update the object below with actual values
const example = {
  "playerRating": null,
  "playerRatingOvertime": null,
} satisfies PlayerRatingData

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerRatingData
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


