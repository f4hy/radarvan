
# PowerStats

The powers page payload: who can be picked, and the picked player.

## Properties

Name | Type
------------ | -------------
`players` | Array&lt;string&gt;
`matches` | number
`profile` | [PlayerPowerProfile](PlayerPowerProfile.md)

## Example

```typescript
import type { PowerStats } from ''

// TODO: Update the object below with actual values
const example = {
  "players": null,
  "matches": null,
  "profile": null,
} satisfies PowerStats

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PowerStats
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


