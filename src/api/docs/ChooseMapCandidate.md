
# ChooseMapCandidate


## Properties

Name | Type
------------ | -------------
`mapName` | string
`votes` | number
`vetoes` | number
`weight` | number
`eligible` | boolean
`recentlyPlayed` | boolean

## Example

```typescript
import type { ChooseMapCandidate } from ''

// TODO: Update the object below with actual values
const example = {
  "mapName": null,
  "votes": null,
  "vetoes": null,
  "weight": null,
  "eligible": null,
  "recentlyPlayed": null,
} satisfies ChooseMapCandidate

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ChooseMapCandidate
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


