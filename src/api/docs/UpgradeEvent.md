
# UpgradeEvent


## Properties

Name | Type
------------ | -------------
`playerName` | string
`timecode` | number
`upgradeName` | string
`cost` | number
`atMinute` | number

## Example

```typescript
import type { UpgradeEvent } from ''

// TODO: Update the object below with actual values
const example = {
  "playerName": null,
  "timecode": null,
  "upgradeName": null,
  "cost": null,
  "atMinute": null,
} satisfies UpgradeEvent

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as UpgradeEvent
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


