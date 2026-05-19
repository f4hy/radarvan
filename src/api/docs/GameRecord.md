
# GameRecord


## Properties

Name | Type
------------ | -------------
`jsonS3Uri` | string
`fileSizeBytes` | number
`gameTimestamp` | Date
`matchId` | number
`replayFileUrl` | string
`replayPresignedUrl` | string
`jsonPresignedUrl` | string
`createdAt` | Date
`gameDate` | Date
`gameVersion` | string
`match` | [MatchListing](MatchListing.md)

## Example

```typescript
import type { GameRecord } from ''

// TODO: Update the object below with actual values
const example = {
  "jsonS3Uri": null,
  "fileSizeBytes": null,
  "gameTimestamp": null,
  "matchId": null,
  "replayFileUrl": null,
  "replayPresignedUrl": null,
  "jsonPresignedUrl": null,
  "createdAt": null,
  "gameDate": null,
  "gameVersion": null,
  "match": null,
} satisfies GameRecord

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameRecord
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


