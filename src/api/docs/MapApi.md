# MapApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**backfillMapCrcsApiBackfillMapCrcsPost**](MapApi.md#backfillmapcrcsapibackfillmapcrcspost) | **POST** /api/backfill_map_crcs | Backfill Map Crcs |
| [**deleteMapDataApiMapDataMapNameDelete**](MapApi.md#deletemapdataapimapdatamapnamedelete) | **DELETE** /api/map_data/{map_name} | Delete Map Data |
| [**fetchMapForMatchApiFetchMapForMatchMatchIdPost**](MapApi.md#fetchmapformatchapifetchmapformatchmatchidpost) | **POST** /api/fetch_map_for_match/{match_id} | Fetch Map For Match |
| [**getMapDataApiMapDataMapNameGet**](MapApi.md#getmapdataapimapdatamapnameget) | **GET** /api/map_data/{map_name} | Get Map Data |
| [**getMapImageApiMapImageMapNameGet**](MapApi.md#getmapimageapimapimagemapnameget) | **GET** /api/map_image/{map_name} | Get Map Image |
| [**getMapMatchCountsApiMapMatchCountsGet**](MapApi.md#getmapmatchcountsapimapmatchcountsget) | **GET** /api/map_match_counts | Get Map Match Counts |
| [**getMapStatsApiMapStatsGet**](MapApi.md#getmapstatsapimapstatsget) | **GET** /api/map_stats/ | Get Map Stats |
| [**getMapSummaryApiMapSummaryPost**](MapApi.md#getmapsummaryapimapsummarypost) | **POST** /api/map_summary/ | Get Map Summary |
| [**getMapsByPlayerCountApiMapsByPlayerCountGet**](MapApi.md#getmapsbyplayercountapimapsbyplayercountget) | **GET** /api/maps_by_player_count | Get Maps By Player Count |
| [**listMissingMapsEndpointApiMissingMapsGet**](MapApi.md#listmissingmapsendpointapimissingmapsget) | **GET** /api/missing_maps | List Missing Maps Endpoint |
| [**mapReparseStatusApiMapReparseStatusGet**](MapApi.md#mapreparsestatusapimapreparsestatusget) | **GET** /api/map_reparse_status | Map Reparse Status |
| [**pushMapsToCncstatsApiPushMapsToCncstatsPost**](MapApi.md#pushmapstocncstatsapipushmapstocncstatspost) | **POST** /api/push_maps_to_cncstats | Push Maps To Cncstats |
| [**renderMapWithPlayersApiMapRenderPost**](MapApi.md#rendermapwithplayersapimaprenderpost) | **POST** /api/map_render | Render Map With Players |
| [**reparseMapsApiReparseMapsPost**](MapApi.md#reparsemapsapireparsemapspost) | **POST** /api/reparse_maps | Reparse Maps |
| [**saveMapDataApiMapDataMapNamePost**](MapApi.md#savemapdataapimapdatamapnamepost) | **POST** /api/map_data/{map_name} | Save Map Data |



## backfillMapCrcsApiBackfillMapCrcsPost

> BackfillMapCrcsResponse backfillMapCrcsApiBackfillMapCrcsPost(maxToUpdate)

Backfill Map Crcs

Fill in MapData.crc from a sample match\&#39;s replay, or the hosted &#x60;.map&#x60; bytes.  For each MapData row missing a CRC, finds a match played on that map and reads the CRC from its parsed replay JSON; for a map nobody has played, computes it from the &#x60;.map&#x60; bytes we host in S3 instead. Resumable (only NULL-CRC rows are touched). Processes up to &#x60;max_to_update&#x60; rows.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { BackfillMapCrcsApiBackfillMapCrcsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies BackfillMapCrcsApiBackfillMapCrcsPostRequest;

  try {
    const data = await api.backfillMapCrcsApiBackfillMapCrcsPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `50`] |

### Return type

[**BackfillMapCrcsResponse**](BackfillMapCrcsResponse.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## deleteMapDataApiMapDataMapNameDelete

> { [key: string]: string | null; } deleteMapDataApiMapDataMapNameDelete(mapName)

Delete Map Data

Delete the MapData row for a map (geometry + CRC + sync state). Dev-only.  Does not touch the &#x60;.map&#x60;/&#x60;.tga&#x60;/&#x60;.webp&#x60; assets in S3 or any match history - only the derived MapData row. For an orphaned map (no matches reference it), that\&#39;s a full removal.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { DeleteMapDataApiMapDataMapNameDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // string
    mapName: mapName_example,
  } satisfies DeleteMapDataApiMapDataMapNameDeleteRequest;

  try {
    const data = await api.deleteMapDataApiMapDataMapNameDelete(body);
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
| **mapName** | `string` |  | [Defaults to `undefined`] |

### Return type

**{ [key: string]: string | null; }**

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## fetchMapForMatchApiFetchMapForMatchMatchIdPost

> FetchMissingMapResult fetchMapForMatchApiFetchMapForMatchMatchIdPost(matchId, parseMap)

Fetch Map For Match

Fetch the cncstats map for a single match\&#39;s MapCRC and upload to S3.  When &#x60;parse_map&#x60; is true and the local mapparse binary is available, also parse the .map and store the geometry payload in &#x60;MapData&#x60;.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { FetchMapForMatchApiFetchMapForMatchMatchIdPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // number
    matchId: 56,
    // boolean (optional)
    parseMap: true,
  } satisfies FetchMapForMatchApiFetchMapForMatchMatchIdPostRequest;

  try {
    const data = await api.fetchMapForMatchApiFetchMapForMatchMatchIdPost(body);
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
| **matchId** | `number` |  | [Defaults to `undefined`] |
| **parseMap** | `boolean` |  | [Optional] [Defaults to `true`] |

### Return type

[**FetchMissingMapResult**](FetchMissingMapResult.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMapDataApiMapDataMapNameGet

> MapDataPayload getMapDataApiMapDataMapNameGet(mapName)

Get Map Data

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { GetMapDataApiMapDataMapNameGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // string
    mapName: mapName_example,
  } satisfies GetMapDataApiMapDataMapNameGetRequest;

  try {
    const data = await api.getMapDataApiMapDataMapNameGet(body);
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
| **mapName** | `string` |  | [Defaults to `undefined`] |

### Return type

[**MapDataPayload**](MapDataPayload.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMapImageApiMapImageMapNameGet

> any getMapImageApiMapImageMapNameGet(mapName)

Get Map Image

Return the WebP for a map, redirecting to its presigned S3 URL.  Resolves to the canonical &#x60;MapData.map_name&#x60; first (case-/whitespace- insensitive), since that\&#39;s stored as the exact S3 asset base name; falls back to case-insensitive variant guesses in S3 for maps with no MapData row.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { GetMapImageApiMapImageMapNameGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapApi();

  const body = {
    // string
    mapName: mapName_example,
  } satisfies GetMapImageApiMapImageMapNameGetRequest;

  try {
    const data = await api.getMapImageApiMapImageMapNameGet(body);
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
| **mapName** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMapMatchCountsApiMapMatchCountsGet

> Array&lt;MapMatchCount&gt; getMapMatchCountsApiMapMatchCountsGet()

Get Map Match Counts

List every map that appears in our match history, with its match count.  Sorted by match count descending.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { GetMapMatchCountsApiMapMatchCountsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  try {
    const data = await api.getMapMatchCountsApiMapMatchCountsGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Array&lt;MapMatchCount&gt;**](MapMatchCount.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMapStatsApiMapStatsGet

> MapStatsResponse getMapStatsApiMapStatsGet()

Get Map Stats

Get player and general win rates grouped by map.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { GetMapStatsApiMapStatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  try {
    const data = await api.getMapStatsApiMapStatsGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**MapStatsResponse**](MapStatsResponse.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMapSummaryApiMapSummaryPost

> string getMapSummaryApiMapSummaryPost(mapSummaryRequest)

Get Map Summary

Return a pre-game summary: map history, team h2h, and per-player records.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { GetMapSummaryApiMapSummaryPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // MapSummaryRequest
    mapSummaryRequest: ...,
  } satisfies GetMapSummaryApiMapSummaryPostRequest;

  try {
    const data = await api.getMapSummaryApiMapSummaryPost(body);
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
| **mapSummaryRequest** | [MapSummaryRequest](MapSummaryRequest.md) |  | |

### Return type

**string**

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMapsByPlayerCountApiMapsByPlayerCountGet

> Array&lt;MapsByPlayerCount&gt; getMapsByPlayerCountApiMapsByPlayerCountGet()

Get Maps By Player Count

Return all maps grouped by number of player starting positions.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { GetMapsByPlayerCountApiMapsByPlayerCountGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  try {
    const data = await api.getMapsByPlayerCountApiMapsByPlayerCountGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Array&lt;MapsByPlayerCount&gt;**](MapsByPlayerCount.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listMissingMapsEndpointApiMissingMapsGet

> Array&lt;MissingMapInfo&gt; listMissingMapsEndpointApiMissingMapsGet(limit)

List Missing Maps Endpoint

Maps referenced by matches that have no MapData row, with their CRC.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { ListMissingMapsEndpointApiMissingMapsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // number (optional)
    limit: 56,
  } satisfies ListMissingMapsEndpointApiMissingMapsGetRequest;

  try {
    const data = await api.listMissingMapsEndpointApiMissingMapsGet(body);
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
| **limit** | `number` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;MissingMapInfo&gt;**](MissingMapInfo.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## mapReparseStatusApiMapReparseStatusGet

> MapReparseStatus mapReparseStatusApiMapReparseStatusGet()

Map Reparse Status

How much work &#x60;POST /api/reparse_maps&#x60; has left: stale rows + missing maps.  &#x60;stale_maps&#x60; compares each MapData row\&#39;s stored &#x60;mapparse_bin_hash&#x60; against the current binary\&#39;s hash (recomputed from the file, so a rebuild is detected without a manual version bump). &#x60;missing_maps&#x60; is maps referenced by matches with no MapData row at all. Both are what &#x60;reparse_maps&#x60; works through; call it repeatedly (it\&#39;s resumable) until both hit 0.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { MapReparseStatusApiMapReparseStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  try {
    const data = await api.mapReparseStatusApiMapReparseStatusGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**MapReparseStatus**](MapReparseStatus.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## pushMapsToCncstatsApiPushMapsToCncstatsPost

> PushMapsResponse pushMapsToCncstatsApiPushMapsToCncstatsPost(maxToUpdate)

Push Maps To Cncstats

Register maps we host (.map + .tga preview, from S3) with cncstats /add_map.  Only considers maps not already marked synced, and checks cncstats /map_exists before pushing - so a map is never sent twice. Pushes run concurrently (bounded by &#x60;_PUSH_CONCURRENCY&#x60;); the CRC + synced mark are then written back serially (one DB session). Processes up to &#x60;max_to_update&#x60; unsynced maps. Requires &#x60;CNCSTATS_API_KEY&#x60;.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { PushMapsToCncstatsApiPushMapsToCncstatsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies PushMapsToCncstatsApiPushMapsToCncstatsPostRequest;

  try {
    const data = await api.pushMapsToCncstatsApiPushMapsToCncstatsPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `10`] |

### Return type

[**PushMapsResponse**](PushMapsResponse.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## renderMapWithPlayersApiMapRenderPost

> any renderMapWithPlayersApiMapRenderPost(mapRenderRequest)

Render Map With Players

Render a map image with player positions (name, general, team color) baked in.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { RenderMapWithPlayersApiMapRenderPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // MapRenderRequest
    mapRenderRequest: ...,
  } satisfies RenderMapWithPlayersApiMapRenderPostRequest;

  try {
    const data = await api.renderMapWithPlayersApiMapRenderPost(body);
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
| **mapRenderRequest** | [MapRenderRequest](MapRenderRequest.md) |  | |

### Return type

**any**

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## reparseMapsApiReparseMapsPost

> ReparseMapsResponse reparseMapsApiReparseMapsPost(maxToUpdate)

Reparse Maps

Bring stored map geometry up to date with the current mapparse binary.  Covers both buckets in one pass, up to &#x60;max_to_update&#x60; total (stale rows first, then missing maps with whatever budget is left):  - Existing rows whose stored geometry predates the current binary:   reparsed from the &#x60;.map&#x60; bytes already in S3, no cncstats call (see   &#x60;missing_maps.reparse_stored_map&#x60;) - cheap and always the bulk of the   work, so it goes first. - Maps referenced by matches with no MapData row yet: fetched fresh from   cncstats and parsed (like the old &#x60;fetch_missing_maps&#x60;). Some of these   may be maps cncstats has never seen either, so they fail every call -   put last so a handful of permanently-missing maps can\&#39;t crowd out the   (fast, reliable) stale reparses batch after batch.  Resumable - call repeatedly (e.g. from a script) until &#x60;remaining&#x60; is 0. Use &#x60;GET /api/map_reparse_status&#x60; to check progress without doing any work.

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { ReparseMapsApiReparseMapsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies ReparseMapsApiReparseMapsPostRequest;

  try {
    const data = await api.reparseMapsApiReparseMapsPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `20`] |

### Return type

[**ReparseMapsResponse**](ReparseMapsResponse.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## saveMapDataApiMapDataMapNamePost

> MapDataPayload saveMapDataApiMapDataMapNamePost(mapName, mapDataPayload)

Save Map Data

### Example

```ts
import {
  Configuration,
  MapApi,
} from '';
import type { SaveMapDataApiMapDataMapNamePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new MapApi(config);

  const body = {
    // string
    mapName: mapName_example,
    // MapDataPayload
    mapDataPayload: ...,
  } satisfies SaveMapDataApiMapDataMapNamePostRequest;

  try {
    const data = await api.saveMapDataApiMapDataMapNamePost(body);
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
| **mapName** | `string` |  | [Defaults to `undefined`] |
| **mapDataPayload** | [MapDataPayload](MapDataPayload.md) |  | |

### Return type

[**MapDataPayload**](MapDataPayload.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

