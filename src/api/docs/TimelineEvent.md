
# TimelineEvent


## Properties

Name | Type
------------ | -------------
`playerName` | string
`atMinute` | number
`eventName` | string
`eventType` | string
`cost` | number

## Example

```typescript
import type { TimelineEvent } from ''

// TODO: Update the object below with actual values
const example = {
  "playerName": null,
  "atMinute": null,
  "eventName": null,
  "eventType": null,
  "cost": null,
} satisfies TimelineEvent

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TimelineEvent
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


