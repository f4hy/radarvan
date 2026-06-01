
# BuildOrder


## Properties

Name | Type
------------ | -------------
`buildings` | [Array&lt;BuildOrderEntry&gt;](BuildOrderEntry.md)
`units` | [Array&lt;BuildOrderEntry&gt;](BuildOrderEntry.md)
`upgrades` | [Array&lt;BuildOrderEntry&gt;](BuildOrderEntry.md)

## Example

```typescript
import type { BuildOrder } from ''

// TODO: Update the object below with actual values
const example = {
  "buildings": null,
  "units": null,
  "upgrades": null,
} satisfies BuildOrder

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BuildOrder
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


