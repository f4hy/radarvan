# MapUploadApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**uploadMapsApiMapUploadPost**](MapUploadApi.md#uploadmapsapimapuploadpost) | **POST** /api/map_upload | Upload Maps |



## uploadMapsApiMapUploadPost

> MapUploadResponse uploadMapsApiMapUploadPost(commit, tga, mapFile, zipFile)

Upload Maps

Preview (commit&#x3D;false) or save (commit&#x3D;true) uploaded maps.  Provide either a &#x60;.tga&#x60; + &#x60;.map&#x60; pair, or a &#x60;.zip&#x60; of folders that each hold a &#x60;.map&#x60; and a &#x60;.tga&#x60; (any other files in a folder are ignored).

### Example

```ts
import {
  Configuration,
  MapUploadApi,
} from '';
import type { UploadMapsApiMapUploadPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapUploadApi();

  const body = {
    // boolean (optional)
    commit: true,
    // string (optional)
    tga: tga_example,
    // string (optional)
    mapFile: mapFile_example,
    // string (optional)
    zipFile: zipFile_example,
  } satisfies UploadMapsApiMapUploadPostRequest;

  try {
    const data = await api.uploadMapsApiMapUploadPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **commit** | `boolean` |  | [Optional] [Defaults to `false`] |
| **tga** | `string` |  | [Optional] [Defaults to `undefined`] |
| **mapFile** | `string` |  | [Optional] [Defaults to `undefined`] |
| **zipFile** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**MapUploadResponse**](MapUploadResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `multipart/form-data`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

