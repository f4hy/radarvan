
# MapDataPayload


## Properties

Name | Type
------------ | -------------
`extent` | [MapExtent](MapExtent.md)
`playerStarts` | [Array&lt;MapPlayerStart&gt;](MapPlayerStart.md)
`supply` | [Array&lt;MapPoint&gt;](MapPoint.md)
`tech` | [Array&lt;MapPoint&gt;](MapPoint.md)
`garrison` | [Array&lt;MapPoint&gt;](MapPoint.md)
`waypoints` | [Array&lt;MapPoint&gt;](MapPoint.md)

## Example

```typescript
import type { MapDataPayload } from ''

// TODO: Update the object below with actual values
const example = {
  "extent": null,
  "playerStarts": null,
  "supply": null,
  "tech": null,
  "garrison": null,
  "waypoints": null,
} satisfies MapDataPayload

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MapDataPayload
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


