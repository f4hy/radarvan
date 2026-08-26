
# PlayerPowers

One player\'s powers in one match: what they bought and what they fired.

## Properties

Name | Type
------------ | -------------
`playerName` | string
`faction` | string
`general` | [General](General.md)
`minutes` | number
`picks` | [Array&lt;PowerPick&gt;](PowerPick.md)
`uses` | [Array&lt;PowerUse&gt;](PowerUse.md)

## Example

```typescript
import type { PlayerPowers } from ''

// TODO: Update the object below with actual values
const example = {
  "playerName": null,
  "faction": null,
  "general": null,
  "minutes": null,
  "picks": null,
  "uses": null,
} satisfies PlayerPowers

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerPowers
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


