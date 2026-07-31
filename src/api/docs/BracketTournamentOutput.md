
# BracketTournamentOutput


## Properties

Name | Type
------------ | -------------
`participantNames` | Array&lt;string&gt;
`players` | [Array&lt;BracketPlayerEntry&gt;](BracketPlayerEntry.md)
`matches` | [Array&lt;BracketMatchOutput&gt;](BracketMatchOutput.md)
`byeAdvances` | [Array&lt;BracketPlayerEntry&gt;](BracketPlayerEntry.md)
`champion` | string
`runnerUp` | string
`needsReset` | boolean
`revealed` | boolean
`revealAt` | Date

## Example

```typescript
import type { BracketTournamentOutput } from ''

// TODO: Update the object below with actual values
const example = {
  "participantNames": null,
  "players": null,
  "matches": null,
  "byeAdvances": null,
  "champion": null,
  "runnerUp": null,
  "needsReset": null,
  "revealed": null,
  "revealAt": null,
} satisfies BracketTournamentOutput

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as BracketTournamentOutput
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


