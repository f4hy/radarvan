
# Player


## Properties

Name | Type
------------ | -------------
`name` | string
`general` | [General](General.md)
`team` | [Team](Team.md)
`color` | string

## Example

```typescript
import type { Player } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "general": null,
  "team": null,
  "color": null,
} satisfies Player

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as Player
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


