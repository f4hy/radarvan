
# TournamentInfo

A tournament in the registry, with how many games are linked to it.

## Properties

Name | Type
------------ | -------------
`slug` | string
`name` | string
`format` | string
`status` | string
`startDate` | Date
`endDate` | Date
`gameCount` | number

## Example

```typescript
import type { TournamentInfo } from ''

// TODO: Update the object below with actual values
const example = {
  "slug": null,
  "name": null,
  "format": null,
  "status": null,
  "startDate": null,
  "endDate": null,
  "gameCount": null,
} satisfies TournamentInfo

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TournamentInfo
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


