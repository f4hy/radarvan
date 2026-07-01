
# FFAStats

Everything the FFA page renders, computed over human free-for-all games.

## Properties

Name | Type
------------ | -------------
`totalGames` | number
`distinctPlayers` | number
`avgPlayersPerGame` | number
`biggestGamePlayers` | number
`playerStats` | [Array&lt;FFAPlayerStat&gt;](FFAPlayerStat.md)
`generalStats` | [Array&lt;FFAGeneralStat&gt;](FFAGeneralStat.md)
`mapStats` | [Array&lt;FFAMapStat&gt;](FFAMapStat.md)

## Example

```typescript
import type { FFAStats } from ''

// TODO: Update the object below with actual values
const example = {
  "totalGames": null,
  "distinctPlayers": null,
  "avgPlayersPerGame": null,
  "biggestGamePlayers": null,
  "playerStats": null,
  "generalStats": null,
  "mapStats": null,
} satisfies FFAStats

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as FFAStats
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


