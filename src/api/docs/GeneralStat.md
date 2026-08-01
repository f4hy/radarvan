
# GeneralStat


## Properties

Name | Type
------------ | -------------
`general` | [General](General.md)
`stats` | [Array&lt;GeneralStatPlayerWL&gt;](GeneralStatPlayerWL.md)
`total` | [WinLoss](WinLoss.md)
`valueDestroyed` | number
`valueLost` | number

## Example

```typescript
import type { GeneralStat } from ''

// TODO: Update the object below with actual values
const example = {
  "general": null,
  "stats": null,
  "total": null,
  "valueDestroyed": null,
  "valueLost": null,
} satisfies GeneralStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GeneralStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


