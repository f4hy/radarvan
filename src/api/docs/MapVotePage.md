
# MapVotePage


## Properties

Name | Type
------------ | -------------
`playerCount` | number
`loggedIn` | boolean
`voteLimit` | number
`vetoLimit` | number
`votesUsed` | number
`vetoesUsed` | number
`maps` | [Array&lt;MapVoteOption&gt;](MapVoteOption.md)

## Example

```typescript
import type { MapVotePage } from ''

// TODO: Update the object below with actual values
const example = {
  "playerCount": null,
  "loggedIn": null,
  "voteLimit": null,
  "vetoLimit": null,
  "votesUsed": null,
  "vetoesUsed": null,
  "maps": null,
} satisfies MapVotePage

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapVotePage
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


