
# FetchMissingMapResult


## Properties

Name | Type
------------ | -------------
`mapName` | string
`baseName` | string
`tgaS3Uri` | string
`webpS3Uri` | string
`mapS3Uri` | string
`error` | string

## Example

```typescript
import type { FetchMissingMapResult } from ''

// TODO: Update the object below with actual values
const example = {
  "mapName": null,
  "baseName": null,
  "tgaS3Uri": null,
  "webpS3Uri": null,
  "mapS3Uri": null,
  "error": null,
} satisfies FetchMissingMapResult

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FetchMissingMapResult
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


