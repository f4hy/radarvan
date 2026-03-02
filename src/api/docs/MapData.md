
# MapData


## Properties

Name | Type
------------ | -------------
`mapName` | string
`totalGames` | number
`playerStats` | [Array&lt;MapPlayerWL&gt;](MapPlayerWL.md)
`generalStats` | [Array&lt;MapGeneralWL&gt;](MapGeneralWL.md)

## Example

```typescript
import type { MapData } from ''

// TODO: Update the object below with actual values
const example = {
  "mapName": null,
  "totalGames": null,
  "playerStats": null,
  "generalStats": null,
} satisfies MapData

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapData
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


