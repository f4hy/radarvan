
# PlayerSynergy

Whether a pair of players over- or under-performs their combined ratings.  ``synergy`` is the extra log-odds the pair\'s team gets purely because the two are paired, beyond what their individual ratings predict (positive = chemistry, negative = anti-synergy). ``win_prob_delta`` expresses the same effect as a win-probability shift at an even (50/50) matchup. See ``SYNERGY_METHODOLOGY.md``.

## Properties

Name | Type
------------ | -------------
`playerA` | string
`playerB` | string
`synergy` | number
`winProbDelta` | number
`gamesTogether` | number
`winsTogether` | number
`expectedWins` | number
`stdError` | number
`zScore` | number
`gamesApart` | number
`mainA` | number
`mainB` | number
`adjustedExpectedWins` | number

## Example

```typescript
import type { PlayerSynergy } from ''

// TODO: Update the object below with actual values
const example = {
  "playerA": null,
  "playerB": null,
  "synergy": null,
  "winProbDelta": null,
  "gamesTogether": null,
  "winsTogether": null,
  "expectedWins": null,
  "stdError": null,
  "zScore": null,
  "gamesApart": null,
  "mainA": null,
  "mainB": null,
  "adjustedExpectedWins": null,
} satisfies PlayerSynergy

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerSynergy
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


