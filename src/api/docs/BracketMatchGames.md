
# BracketMatchGames

The games played for one bracket match, plus what else it could be.  ``linked`` is what\'s persisted. ``candidates`` is what the detector would propose but nobody has confirmed - shown to tournament admins so they can link a game the automatic rule missed (a mismatched alias, a game played on a different night than scheduled).

## Properties

Name | Type
------------ | -------------
`matchId` | string
`linked` | [Array&lt;MatchInfo&gt;](MatchInfo.md)
`candidates` | [Array&lt;MatchInfo&gt;](MatchInfo.md)

## Example

```typescript
import type { BracketMatchGames } from ''

// TODO: Update the object below with actual values
const example = {
  "matchId": null,
  "linked": null,
  "candidates": null,
} satisfies BracketMatchGames

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BracketMatchGames
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


