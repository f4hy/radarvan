
# PushMapsResponse


## Properties

Name | Type
------------ | -------------
`requested` | number
`pushed` | number
`alreadyPresent` | number
`results` | [Array&lt;PushMapResult&gt;](PushMapResult.md)

## Example

```typescript
import type { PushMapsResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "requested": null,
  "pushed": null,
  "alreadyPresent": null,
  "results": null,
} satisfies PushMapsResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PushMapsResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


