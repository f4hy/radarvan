
# PlayerPowerProfile


## Properties

Name | Type
------------ | -------------
`player` | string
`games` | number
`generals` | [Array&lt;GeneralPowers&gt;](GeneralPowers.md)
`unusual` | [Array&lt;UnusualPick&gt;](UnusualPick.md)

## Example

```typescript
import type { PlayerPowerProfile } from ''

// TODO: Update the object below with actual values
const example = {
  "player": null,
  "games": null,
  "generals": null,
  "unusual": null,
} satisfies PlayerPowerProfile

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerPowerProfile
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


