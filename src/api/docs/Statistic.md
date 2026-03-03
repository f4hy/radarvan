
# Statistic


## Properties

Name | Type
------------ | -------------
`statName` | string
`dateComputed` | Date
`value` | [Value](Value.md)
`player` | string
`matchId` | number

## Example

```typescript
import type { Statistic } from ''

// TODO: Update the object below with actual values
const example = {
  "statName": null,
  "dateComputed": null,
  "value": null,
  "player": null,
  "matchId": null,
} satisfies Statistic

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as Statistic
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


