
# ProfileBadge

A top-3 behavioral standout among profiled players for one stat.

## Properties

Name | Type
------------ | -------------
`key` | string
`label` | string
`description` | string
`value` | number
`rank` | number
`tier` | string
`totalPlayers` | number

## Example

```typescript
import type { ProfileBadge } from ''

// TODO: Update the object below with actual values
const example = {
  "key": null,
  "label": null,
  "description": null,
  "value": null,
  "rank": null,
  "tier": null,
  "totalPlayers": null,
} satisfies ProfileBadge

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProfileBadge
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


