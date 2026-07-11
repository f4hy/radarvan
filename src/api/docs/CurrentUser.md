
# CurrentUser


## Properties

Name | Type
------------ | -------------
`discordId` | string
`discordUsername` | string
`discordAvatar` | string
`playerName` | string
`needsPlayerSelection` | boolean
`isAdmin` | boolean
`isTournamentAdmin` | boolean

## Example

```typescript
import type { CurrentUser } from ''

// TODO: Update the object below with actual values
const example = {
  "discordId": null,
  "discordUsername": null,
  "discordAvatar": null,
  "playerName": null,
  "needsPlayerSelection": null,
  "isAdmin": null,
  "isTournamentAdmin": null,
} satisfies CurrentUser

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CurrentUser
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


