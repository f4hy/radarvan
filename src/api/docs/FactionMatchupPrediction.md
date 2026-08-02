
# FactionMatchupPrediction

Every general-vs-general draw for a hypothetical player1 vs player2 matchup, ranked by how favorable it is to player1 (best first).

## Properties

Name | Type
------------ | -------------
`player1` | string
`player2` | string
`mapName` | string
`options` | [Array&lt;FactionMatchupOption&gt;](FactionMatchupOption.md)
`ensembleSize` | number
`computeMs` | number

## Example

```typescript
import type { FactionMatchupPrediction } from ''

// TODO: Update the object below with actual values
const example = {
  "player1": null,
  "player2": null,
  "mapName": null,
  "options": null,
  "ensembleSize": null,
  "computeMs": null,
} satisfies FactionMatchupPrediction

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FactionMatchupPrediction
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


