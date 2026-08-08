
# PlayerRole

The kind of slot a player occupied.  HUMAN and CPU are both *competitors* - they play the game and belong to a team. OBSERVER covers spectators and any slot the header doesn\'t report as human or computer (empty/disconnected slots).

## Properties

Name | Type
------------ | -------------

## Example

```typescript
import type { PlayerRole } from ''

// TODO: Update the object below with actual values
const example = {
} satisfies PlayerRole

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerRole
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


