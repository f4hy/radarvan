
# ReplayWithoutPlayerStats

A parsed replay still missing player stats (backfill work item).

## Properties

Name | Type
------------ | -------------
`matchId` | number
`url` | string
`s3Path` | string
`version` | string
`presignedUrl` | string
`allReplayUrls` | Array&lt;string&gt;

## Example

```typescript
import type { ReplayWithoutPlayerStats } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "url": null,
  "s3Path": null,
  "version": null,
  "presignedUrl": null,
  "allReplayUrls": null,
} satisfies ReplayWithoutPlayerStats

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ReplayWithoutPlayerStats
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


