
# GameComposition

Detailed composition information about an RTS game.

## Properties

Name | Type
------------ | -------------
`category` | string
`isCompStomp` | boolean
`isFfa` | boolean
`numTeams` | number
`teamSizes` | Array&lt;number&gt;
`totalPlayers` | number
`numHumans` | number
`numComputers` | number
`isBalanced` | boolean
`is1V1` | boolean
`isTeamGame` | boolean

## Example

```typescript
import type { GameComposition } from ''

// TODO: Update the object below with actual values
const example = {
  "category": null,
  "isCompStomp": null,
  "isFfa": null,
  "numTeams": null,
  "teamSizes": null,
  "totalPlayers": null,
  "numHumans": null,
  "numComputers": null,
  "isBalanced": null,
  "is1V1": null,
  "isTeamGame": null,
} satisfies GameComposition

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameComposition
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


