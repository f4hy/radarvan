
# ChooseMapResult


## Properties

Name | Type
------------ | -------------
`playerCount` | number
`chosenMap` | string
`candidates` | [Array&lt;ChooseMapCandidate&gt;](ChooseMapCandidate.md)

## Example

```typescript
import type { ChooseMapResult } from ''

// TODO: Update the object below with actual values
const example = {
  "playerCount": null,
  "chosenMap": null,
  "candidates": null,
} satisfies ChooseMapResult

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ChooseMapResult
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


