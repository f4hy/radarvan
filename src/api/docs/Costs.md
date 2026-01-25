
# Costs


## Properties

Name | Type
------------ | -------------
`player` | [Player](Player.md)
`buildings` | [Array&lt;CostsBuiltObject&gt;](CostsBuiltObject.md)
`units` | [Array&lt;CostsBuiltObject&gt;](CostsBuiltObject.md)
`upgrades` | [Array&lt;CostsBuiltObject&gt;](CostsBuiltObject.md)

## Example

```typescript
import type { Costs } from ''

// TODO: Update the object below with actual values
const example = {
  "player": null,
  "buildings": null,
  "units": null,
  "upgrades": null,
} satisfies Costs

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as Costs
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


