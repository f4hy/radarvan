
# GameNightHighlight

One notable thing that happened, ready to render as a card.  ``kind`` is a stable slug (\"longest_game\", \"upset\", \"first_blood\", ...) the frontend maps to an icon; ``title`` and ``detail`` are already human-readable, so an unrecognised kind still renders correctly.

## Properties

Name | Type
------------ | -------------
`kind` | string
`title` | string
`detail` | string
`matchId` | number

## Example

```typescript
import type { GameNightHighlight } from ''

// TODO: Update the object below with actual values
const example = {
  "kind": null,
  "title": null,
  "detail": null,
  "matchId": null,
} satisfies GameNightHighlight

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameNightHighlight
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


