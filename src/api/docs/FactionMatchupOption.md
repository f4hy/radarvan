
# FactionMatchupOption

One (player1_general, player2_general) draw and its predicted outcome.

## Properties

Name | Type
------------ | -------------
`player1General` | [General](General.md)
`player2General` | [General](General.md)
`probPlayer1Wins` | number

## Example

```typescript
import type { FactionMatchupOption } from ''

// TODO: Update the object below with actual values
const example = {
  "player1General": null,
  "player2General": null,
  "probPlayer1Wins": null,
} satisfies FactionMatchupOption

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FactionMatchupOption
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


