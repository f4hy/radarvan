
# KillEventOutput


## Properties

Name | Type
------------ | -------------
`atMinute` | number
`killerPlayer` | string
`victimPlayer` | string
`x` | number
`y` | number
`killer` | string
`victim` | string
`damageType` | string

## Example

```typescript
import type { KillEventOutput } from ''

// TODO: Update the object below with actual values
const example = {
  "atMinute": null,
  "killerPlayer": null,
  "victimPlayer": null,
  "x": null,
  "y": null,
  "killer": null,
  "victim": null,
  "damageType": null,
} satisfies KillEventOutput

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as KillEventOutput
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


