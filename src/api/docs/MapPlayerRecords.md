
# MapPlayerRecords

One map, and how everyone who played it did on it.  ``map_key`` is ``replay_files.map_key`` - the normalized join key a caller can match against its own map list; ``map_name`` is the raw basename as stored on the match, for display when nothing matches. ``total_games`` counts games, not player-results, so it isn\'t the sum of the per-player records.

## Properties

Name | Type
------------ | -------------
`mapKey` | string
`mapName` | string
`totalGames` | number
`players` | [Array&lt;MapPlayerWL&gt;](MapPlayerWL.md)

## Example

```typescript
import type { MapPlayerRecords } from ''

// TODO: Update the object below with actual values
const example = {
  "mapKey": null,
  "mapName": null,
  "totalGames": null,
  "players": null,
} satisfies MapPlayerRecords

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapPlayerRecords
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


