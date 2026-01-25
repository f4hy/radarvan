
# PlayerListing


## Properties

Name | Type
------------ | -------------
`id` | number
`playerName` | string
`teamId` | number
`isWinner` | boolean
`generalId` | number
`matchId` | number
`color` | string

## Example

```typescript
import type { PlayerListing } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "playerName": null,
  "teamId": null,
  "isWinner": null,
  "generalId": null,
  "matchId": null,
  "color": null,
} satisfies PlayerListing

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerListing
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


