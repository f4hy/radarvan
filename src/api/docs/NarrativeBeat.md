
# NarrativeBeat

One sentence of the story, optionally pinned to a minute.  ``kind`` groups beats for styling and is one of: \"setup\" (map, format, lineup - no minute), \"first_blood\", \"milestone\" (rank 5, search & destroy), \"superweapon\", \"collapse\" (went hunted, lost power), \"economy\", \"damage\", \"tempo\" (APM), \"result\". The frontend maps it to an icon; an unknown kind must render as a plain bullet rather than break the list.

## Properties

Name | Type
------------ | -------------
`kind` | string
`text` | string
`atMinute` | number
`playerName` | string

## Example

```typescript
import type { NarrativeBeat } from ''

// TODO: Update the object below with actual values
const example = {
  "kind": null,
  "text": null,
  "atMinute": null,
  "playerName": null,
} satisfies NarrativeBeat

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as NarrativeBeat
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


