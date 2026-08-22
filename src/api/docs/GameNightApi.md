# GameNightApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getGameNightRecapApiGameNightNightGet**](GameNightApi.md#getgamenightrecapapigamenightnightget) | **GET** /api/game_night/{night} | Get Game Night Recap |
| [**getGameNightSummaryStatusApiGameNightStatusNightGet**](GameNightApi.md#getgamenightsummarystatusapigamenightstatusnightget) | **GET** /api/game_night_status/{night} | Get Game Night Summary Status |
| [**listGameNightSummariesApiGameNightSummariesGet**](GameNightApi.md#listgamenightsummariesapigamenightsummariesget) | **GET** /api/game_night_summaries | List Game Night Summaries |



## getGameNightRecapApiGameNightNightGet

> GameNightRecap getGameNightRecapApiGameNightNightGet(night)

Get Game Night Recap

The recap for one game night.  &#x60;&#x60;night&#x60;&#x60; is the game-night date key (&#x60;&#x60;utils.game_night_date&#x60;&#x60;), the same one &#x60;&#x60;/api/dates/&#x60;&#x60; returns - not a calendar UTC date. A night with no games returns a zeroed recap rather than a 404, so the page can render \&quot;nothing was played\&quot; for a date somebody typed in.

### Example

```ts
import {
  Configuration,
  GameNightApi,
} from '';
import type { GetGameNightRecapApiGameNightNightGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new GameNightApi(config);

  const body = {
    // Date
    night: 2013-10-20,
  } satisfies GetGameNightRecapApiGameNightNightGetRequest;

  try {
    const data = await api.getGameNightRecapApiGameNightNightGet(body);
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
| **night** | `Date` |  | [Defaults to `undefined`] |

### Return type

[**GameNightRecap**](GameNightRecap.md)

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


## getGameNightSummaryStatusApiGameNightStatusNightGet

> GameNightSummaryStatus getGameNightSummaryStatusApiGameNightStatusNightGet(night)

Get Game Night Summary Status

Whether a night has a stored LLM recap, without shipping its text.

### Example

```ts
import {
  Configuration,
  GameNightApi,
} from '';
import type { GetGameNightSummaryStatusApiGameNightStatusNightGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new GameNightApi(config);

  const body = {
    // Date
    night: 2013-10-20,
  } satisfies GetGameNightSummaryStatusApiGameNightStatusNightGetRequest;

  try {
    const data = await api.getGameNightSummaryStatusApiGameNightStatusNightGet(body);
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
| **night** | `Date` |  | [Defaults to `undefined`] |

### Return type

[**GameNightSummaryStatus**](GameNightSummaryStatus.md)

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


## listGameNightSummariesApiGameNightSummariesGet

> Array&lt;Date&gt; listGameNightSummariesApiGameNightSummariesGet(limit)

List Game Night Summaries

Game nights that have a stored LLM recap, newest first.  Lets a listing badge the nights that have one without fetching each night\&#39;s recap. A distinct top-level path rather than a static sibling of &#x60;&#x60;/api/game_night/{night}&#x60;&#x60; - the OpenAPI generator silently merges those (see the maps note in CLAUDE.md).

### Example

```ts
import {
  Configuration,
  GameNightApi,
} from '';
import type { ListGameNightSummariesApiGameNightSummariesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new GameNightApi(config);

  const body = {
    // number (optional)
    limit: 56,
  } satisfies ListGameNightSummariesApiGameNightSummariesGetRequest;

  try {
    const data = await api.listGameNightSummariesApiGameNightSummariesGet(body);
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
| **limit** | `number` |  | [Optional] [Defaults to `60`] |

### Return type

**Array<Date>**

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

