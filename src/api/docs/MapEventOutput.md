
# MapEventOutput

A single map-positioned, time-stamped event for replay playback.  `kind` is one of \"build\" (structure completed) or \"capture\" (neutral/enemy structure taken). `player_name` is the owner after the event; `name` is the cleaned object name. Kill events are served separately via `kill_events`.

## Properties

Name | Type
------------ | -------------
`atMinute` | number
`x` | number
`y` | number
`playerName` | string
`kind` | string
`name` | string

## Example

```typescript
import type { MapEventOutput } from ''

// TODO: Update the object below with actual values
const example = {
  "atMinute": null,
  "x": null,
  "y": null,
  "playerName": null,
  "kind": null,
  "name": null,
} satisfies MapEventOutput

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapEventOutput
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


