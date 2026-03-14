
# DraftAssignment


## Properties

Name | Type
------------ | -------------
`playerName` | string
`team` | number
`positionNumber` | number
`general` | number

## Example

```typescript
import type { DraftAssignment } from ''

// TODO: Update the object below with actual values
const example = {
  "playerName": null,
  "team": null,
  "positionNumber": null,
  "general": null,
} satisfies DraftAssignment

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as DraftAssignment
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


