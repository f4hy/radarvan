
# MapReparseStatus


## Properties

Name | Type
------------ | -------------
`totalMaps` | number
`staleMaps` | number
`missingMaps` | number
`mapparseAvailable` | boolean
`currentMapparseHash` | string

## Example

```typescript
import type { MapReparseStatus } from ''

// TODO: Update the object below with actual values
const example = {
  "totalMaps": null,
  "staleMaps": null,
  "missingMaps": null,
  "mapparseAvailable": null,
  "currentMapparseHash": null,
} satisfies MapReparseStatus

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapReparseStatus
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


