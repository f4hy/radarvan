
# MatchInfo


## Properties

Name | Type
------------ | -------------
`id` | number
`timestamp` | Date
`date` | Date
`map` | string
`winningTeam` | [Team](Team.md)
`players` | [Array&lt;Player&gt;](Player.md)
`durationMinutes` | number
`filename` | string
`incomplete` | string
`notes` | string
`gameVersion` | string
`composition` | [GameComposition](GameComposition.md)
`isDev` | boolean

## Example

```typescript
import type { MatchInfo } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "timestamp": null,
  "date": null,
  "map": null,
  "winningTeam": null,
  "players": null,
  "durationMinutes": null,
  "filename": null,
  "incomplete": null,
  "notes": null,
  "gameVersion": null,
  "composition": null,
  "isDev": null,
} satisfies MatchInfo

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MatchInfo
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


