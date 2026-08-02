
# FactionMatrix

The full general-vs-general grid with both players and the map forced to the model\'s UNK slot - i.e. a pure faction-vs-faction signal, not tied to any specific players. ``median_prob_a_wins`` is the median across all cells; callers derive \"above/below median\" from it rather than reading ``prob_a_wins`` as an absolute probability.

## Properties

Name | Type
------------ | -------------
`mapName` | string
`medianProbAWins` | number
`cells` | [Array&lt;FactionMatrixCell&gt;](FactionMatrixCell.md)
`computeMs` | number

## Example

```typescript
import type { FactionMatrix } from ''

// TODO: Update the object below with actual values
const example = {
  "mapName": null,
  "medianProbAWins": null,
  "cells": null,
  "computeMs": null,
} satisfies FactionMatrix

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FactionMatrix
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


