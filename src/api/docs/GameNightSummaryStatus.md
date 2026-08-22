
# GameNightSummaryStatus

Whether a night\'s LLM summary exists, without shipping its text.  Used by the ops panel to see what the nightly job has and hasn\'t written.

## Properties

Name | Type
------------ | -------------
`date` | Date
`hasSummary` | boolean
`provider` | string
`computedAt` | Date

## Example

```typescript
import type { GameNightSummaryStatus } from ''

// TODO: Update the object below with actual values
const example = {
  "date": null,
  "hasSummary": null,
  "provider": null,
  "computedAt": null,
} satisfies GameNightSummaryStatus

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GameNightSummaryStatus
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


