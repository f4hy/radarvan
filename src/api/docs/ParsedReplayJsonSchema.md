
# ParsedReplayJsonSchema

Public API representation of ParsedReplayJson

## Properties

Name | Type
------------ | -------------
`jsonS3Uri` | string
`matchId` | number
`replayFileUrl` | string
`numTimeStamps` | number
`createdAt` | Date
`gameTimestamp` | Date
`gameDate` | Date
`updatedAt` | Date
`hasEnhancedStats` | boolean

## Example

```typescript
import type { ParsedReplayJsonSchema } from ''

// TODO: Update the object below with actual values
const example = {
  "jsonS3Uri": null,
  "matchId": null,
  "replayFileUrl": null,
  "numTimeStamps": null,
  "createdAt": null,
  "gameTimestamp": null,
  "gameDate": null,
  "updatedAt": null,
  "hasEnhancedStats": null,
} satisfies ParsedReplayJsonSchema

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ParsedReplayJsonSchema
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


