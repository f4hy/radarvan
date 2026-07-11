
# OpponentProfileStat

The profiled player\'s record against one opponent (wins = subject\'s wins).

## Properties

Name | Type
------------ | -------------
`name` | string
`wins` | number
`losses` | number

## Example

```typescript
import type { OpponentProfileStat } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "wins": null,
  "losses": null,
} satisfies OpponentProfileStat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as OpponentProfileStat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


