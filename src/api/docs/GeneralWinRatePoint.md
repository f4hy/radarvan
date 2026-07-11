
# GeneralWinRatePoint

One point in a player\'s running win-rate-over-time series for a general.  ``wins``/``losses`` are cumulative as of this game (not just this game\'s result), so plotting ``win_rate`` against ``game_number`` traces how the player\'s record on this general evolved.

## Properties

Name | Type
------------ | -------------
`date` | Date
`gameNumber` | number
`wins` | number
`losses` | number
`winRate` | number

## Example

```typescript
import type { GeneralWinRatePoint } from ''

// TODO: Update the object below with actual values
const example = {
  "date": null,
  "gameNumber": null,
  "wins": null,
  "losses": null,
  "winRate": null,
} satisfies GeneralWinRatePoint

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GeneralWinRatePoint
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


