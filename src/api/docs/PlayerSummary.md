
# PlayerSummary


## Properties

Name | Type
------------ | -------------
`name` | string
`side` | string
`team` | number
`win` | boolean
`color` | string
`unitsCreated` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)
`buildingsBuilt` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)
`upgradesBuilt` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)
`powersUsed` | { [key: string]: number; }
`unitsDestroyed` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)
`buildingsDestroyed` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)
`unitsLost` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)
`buildingsLost` | [{ [key: string]: ObjectSummary; }](ObjectSummary.md)

## Example

```typescript
import type { PlayerSummary } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "side": null,
  "team": null,
  "win": null,
  "color": null,
  "unitsCreated": null,
  "buildingsBuilt": null,
  "upgradesBuilt": null,
  "powersUsed": null,
  "unitsDestroyed": null,
  "buildingsDestroyed": null,
  "unitsLost": null,
  "buildingsLost": null,
} satisfies PlayerSummary

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as PlayerSummary
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


