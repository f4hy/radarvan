
# MapUploadResponse


## Properties

Name | Type
------------ | -------------
`committed` | boolean
`maps` | [Array&lt;MapUploadItem&gt;](MapUploadItem.md)
`errors` | Array&lt;string&gt;

## Example

```typescript
import type { MapUploadResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "committed": null,
  "maps": null,
  "errors": null,
} satisfies MapUploadResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapUploadResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


