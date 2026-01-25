
# Tournament


## Properties

Name | Type
------------ | -------------
`name` | string
`startDate` | Date
`endDate` | Date
`teams` | Array&lt;Array&lt;string&gt;&gt;
`totalGamesPlayedPerTeam` | number

## Example

```typescript
import type { Tournament } from ''

// TODO: Update the object below with actual values
const example = {
  "name": null,
  "startDate": null,
  "endDate": null,
  "teams": null,
  "totalGamesPlayedPerTeam": null,
} satisfies Tournament

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as Tournament
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


