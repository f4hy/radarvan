
# ReplayFileSchema

Public API representation of ReplayFile

## Properties

Name | Type
------------ | -------------
`originalUrl` | string
`s3Uri` | string
`status` | string
`playerId` | string
`discoveredAt` | Date
`sourceDate` | Date

## Example

```typescript
import type { ReplayFileSchema } from ''

// TODO: Update the object below with actual values
const example = {
  "originalUrl": null,
  "s3Uri": null,
  "status": null,
  "playerId": null,
  "discoveredAt": null,
  "sourceDate": null,
} satisfies ReplayFileSchema

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ReplayFileSchema
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


