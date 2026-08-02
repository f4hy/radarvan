
# FactionMatrixCell

One (general_a, general_b) cell of the player-agnostic faction matrix.  ``prob_a_wins`` is the ensemble mean; ``prob_a_wins_std`` is the spread across replicates. ``significant`` is True when the cell\'s ~90% empirical interval across the ensemble excludes 0.5 - i.e. this general pairing looks real rather than indistinguishable from a coin flip given how little training data there is (see ``ml.bootstrap_matrix``).

## Properties

Name | Type
------------ | -------------
`generalA` | [General](General.md)
`generalB` | [General](General.md)
`probAWins` | number
`probAWinsStd` | number
`significant` | boolean

## Example

```typescript
import type { FactionMatrixCell } from ''

// TODO: Update the object below with actual values
const example = {
  "generalA": null,
  "generalB": null,
  "probAWins": null,
  "probAWinsStd": null,
  "significant": null,
} satisfies FactionMatrixCell

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FactionMatrixCell
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


