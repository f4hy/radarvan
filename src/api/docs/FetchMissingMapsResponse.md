
# FetchMissingMapsResponse


## Properties

Name | Type
------------ | -------------
`requested` | number
`fetched` | number
`results` | [Array&lt;FetchMissingMapResult&gt;](FetchMissingMapResult.md)

## Example

```typescript
import type { FetchMissingMapsResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "requested": null,
  "fetched": null,
  "results": null,
} satisfies FetchMissingMapsResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FetchMissingMapsResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


