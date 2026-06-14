# MapVoteApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**chooseMapApiMapVotePlayerCountChoosePost**](MapVoteApi.md#choosemapapimapvoteplayercountchoosepost) | **POST** /api/map_vote/{player_count}/choose | Choose Map |
| [**getVotePageApiMapVotePlayerCountGet**](MapVoteApi.md#getvotepageapimapvoteplayercountget) | **GET** /api/map_vote/{player_count} | Get Vote Page |
| [**playerCountsApiMapVotePlayerCountsGet**](MapVoteApi.md#playercountsapimapvoteplayercountsget) | **GET** /api/map_vote/player_counts | Player Counts |
| [**setVoteApiMapVotePlayerCountPost**](MapVoteApi.md#setvoteapimapvoteplayercountpost) | **POST** /api/map_vote/{player_count} | Set Vote |
| [**votingPlayersApiMapVotePlayersGet**](MapVoteApi.md#votingplayersapimapvoteplayersget) | **GET** /api/map_vote/players | Voting Players |



## chooseMapApiMapVotePlayerCountChoosePost

> ChooseMapResult chooseMapApiMapVotePlayerCountChoosePost(playerCount, chooseMapRequest)

Choose Map

Run the authoritative weighted-random draw for this player count.  Only the votes of the players in &#x60;&#x60;req.players&#x60;&#x60; are counted, so the draw reflects who\&#39;s actually playing. Returns the chosen map plus every voted/vetoed map (with tallies) for the frontend\&#39;s reveal + spin.

### Example

```ts
import {
  Configuration,
  MapVoteApi,
} from '';
import type { ChooseMapApiMapVotePlayerCountChoosePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapVoteApi();

  const body = {
    // number
    playerCount: 56,
    // ChooseMapRequest
    chooseMapRequest: ...,
  } satisfies ChooseMapApiMapVotePlayerCountChoosePostRequest;

  try {
    const data = await api.chooseMapApiMapVotePlayerCountChoosePost(body);
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
| **playerCount** | `number` |  | [Defaults to `undefined`] |
| **chooseMapRequest** | [ChooseMapRequest](ChooseMapRequest.md) |  | |

### Return type

[**ChooseMapResult**](ChooseMapResult.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getVotePageApiMapVotePlayerCountGet

> MapVotePage getVotePageApiMapVotePlayerCountGet(playerCount)

Get Vote Page

Maps for a player count (ordered by total games) plus the viewer\&#39;s picks.

### Example

```ts
import {
  Configuration,
  MapVoteApi,
} from '';
import type { GetVotePageApiMapVotePlayerCountGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapVoteApi();

  const body = {
    // number
    playerCount: 56,
  } satisfies GetVotePageApiMapVotePlayerCountGetRequest;

  try {
    const data = await api.getVotePageApiMapVotePlayerCountGet(body);
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
| **playerCount** | `number` |  | [Defaults to `undefined`] |

### Return type

[**MapVotePage**](MapVotePage.md)

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


## playerCountsApiMapVotePlayerCountsGet

> Array&lt;number | null&gt; playerCountsApiMapVotePlayerCountsGet()

Player Counts

Player counts (map capacities) that have at least one known map.

### Example

```ts
import {
  Configuration,
  MapVoteApi,
} from '';
import type { PlayerCountsApiMapVotePlayerCountsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapVoteApi();

  try {
    const data = await api.playerCountsApiMapVotePlayerCountsGet();
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

**Array<number | null>**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## setVoteApiMapVotePlayerCountPost

> MapVotePage setVoteApiMapVotePlayerCountPost(playerCount, setMapVoteRequest)

Set Vote

Cast/clear a vote or veto for a map (requires login).

### Example

```ts
import {
  Configuration,
  MapVoteApi,
} from '';
import type { SetVoteApiMapVotePlayerCountPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapVoteApi();

  const body = {
    // number
    playerCount: 56,
    // SetMapVoteRequest
    setMapVoteRequest: ...,
  } satisfies SetVoteApiMapVotePlayerCountPostRequest;

  try {
    const data = await api.setVoteApiMapVotePlayerCountPost(body);
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
| **playerCount** | `number` |  | [Defaults to `undefined`] |
| **setMapVoteRequest** | [SetMapVoteRequest](SetMapVoteRequest.md) |  | |

### Return type

[**MapVotePage**](MapVotePage.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## votingPlayersApiMapVotePlayersGet

> Array&lt;string | null&gt; votingPlayersApiMapVotePlayersGet()

Voting Players

In-game names with an account — the selectable participants for a draw.

### Example

```ts
import {
  Configuration,
  MapVoteApi,
} from '';
import type { VotingPlayersApiMapVotePlayersGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new MapVoteApi();

  try {
    const data = await api.votingPlayersApiMapVotePlayersGet();
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

**Array<string | null>**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

