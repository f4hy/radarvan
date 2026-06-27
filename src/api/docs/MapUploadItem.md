
# MapUploadItem


## Properties

Name | Type
------------ | -------------
`baseName` | string
`image` | string
`playerCount` | number
`alreadyExists` | boolean
`saved` | boolean
`crc` | string
`pushedToCncstats` | boolean

## Example

```typescript
import type { MapUploadItem } from ''

// TODO: Update the object below with actual values
const example = {
  "baseName": null,
  "image": null,
  "playerCount": null,
  "alreadyExists": null,
  "saved": null,
  "crc": null,
  "pushedToCncstats": null,
} satisfies MapUploadItem

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapUploadItem
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


