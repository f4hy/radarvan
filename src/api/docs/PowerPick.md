
# PowerPick

One `PurchaseScience` order: a generals point spent.  Deliberately just the raw id and when it was bought. The *name* of a science is a property of the game\'s science list, not of this match, and `generals_powers` resolves it at read time - so identifying an id we currently can\'t name is a one-line table edit rather than a DETAILS_VERSION bump and a re-derivation of every cached match.

## Properties

Name | Type
------------ | -------------
`atMinute` | number
`scienceId` | number

## Example

```typescript
import type { PowerPick } from ''

// TODO: Update the object below with actual values
const example = {
  "atMinute": null,
  "scienceId": null,
} satisfies PowerPick

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PowerPick
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


