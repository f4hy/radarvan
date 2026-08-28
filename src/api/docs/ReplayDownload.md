
# ReplayDownload

A presigned .rep URL plus the name the browser should save it under.  The name travels with the URL because it is derived from the match (date, sides, map) rather than from the S3 key, which is a content hash.

## Properties

Name | Type
------------ | -------------
`url` | string
`filename` | string

## Example

```typescript
import type { ReplayDownload } from ''

// TODO: Update the object below with actual values
const example = {
  "url": null,
  "filename": null,
} satisfies ReplayDownload

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ReplayDownload
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


