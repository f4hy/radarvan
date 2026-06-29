
# HeadToHeadGame


## Properties

Name | Type
------------ | -------------
`matchId` | number
`timestamp` | Date
`date` | Date
`map` | string
`durationMinutes` | number
`gameFormat` | string
`player1General` | [General](General.md)
`player2General` | [General](General.md)
`player1Won` | boolean
`player1Team` | Array&lt;string&gt;
`player2Team` | Array&lt;string&gt;

## Example

```typescript
import type { HeadToHeadGame } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "timestamp": null,
  "date": null,
  "map": null,
  "durationMinutes": null,
  "gameFormat": null,
  "player1General": null,
  "player2General": null,
  "player1Won": null,
  "player1Team": null,
  "player2Team": null,
} satisfies HeadToHeadGame

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as HeadToHeadGame
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


