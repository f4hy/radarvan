
# MatchupCommentaryPromptPreview

The exact system + user content that would be sent to the active LLM provider, plus character counts - for inspecting/trimming payload size without spending a real API call. Shared by both dev-only preview endpoints (pre-game matchup, post-game recap); see routes/commentary.py.

## Properties

Name | Type
------------ | -------------
`system` | string
`userMessage` | string
`systemChars` | number
`userMessageChars` | number

## Example

```typescript
import type { MatchupCommentaryPromptPreview } from ''

// TODO: Update the object below with actual values
const example = {
  "system": null,
  "userMessage": null,
  "systemChars": null,
  "userMessageChars": null,
} satisfies MatchupCommentaryPromptPreview

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MatchupCommentaryPromptPreview
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


