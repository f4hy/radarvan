# BracketApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createBracketApiBracketPost**](BracketApi.md#createbracketapibracketpost) | **POST** /api/bracket | Create Bracket |
| [**eligiblePlayersApiBracketEligiblePlayersGet**](BracketApi.md#eligibleplayersapibracketeligibleplayersget) | **GET** /api/bracket_eligible_players | Eligible Players |
| [**getBracketApiBracketGet**](BracketApi.md#getbracketapibracketget) | **GET** /api/bracket | Get Bracket |
| [**setBracketMatchApiBracketMatchIdPost**](BracketApi.md#setbracketmatchapibracketmatchidpost) | **POST** /api/bracket/{match_id} | Set Bracket Match |
| [**setBracketRevealAtApiBracketRevealAtPost**](BracketApi.md#setbracketrevealatapibracketrevealatpost) | **POST** /api/bracket/reveal_at | Set Bracket Reveal At |



## createBracketApiBracketPost

> BracketTournamentOutput createBracketApiBracketPost(createBracketRequest)

Create Bracket

Create (or replace) the bracket with these 9-16 seeded entrants.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { CreateBracketApiBracketPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  const body = {
    // CreateBracketRequest
    createBracketRequest: ...,
  } satisfies CreateBracketApiBracketPostRequest;

  try {
    const data = await api.createBracketApiBracketPost(body);
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
| **createBracketRequest** | [CreateBracketRequest](CreateBracketRequest.md) |  | |

### Return type

[**BracketTournamentOutput**](BracketTournamentOutput.md)

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


## eligiblePlayersApiBracketEligiblePlayersGet

> Array&lt;string | null&gt; eligiblePlayersApiBracketEligiblePlayersGet()

Eligible Players

Known player names - the pool admins pick the 9-16 entrants from.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { EligiblePlayersApiBracketEligiblePlayersGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  try {
    const data = await api.eligiblePlayersApiBracketEligiblePlayersGet();
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


## getBracketApiBracketGet

> BracketTournamentOutput getBracketApiBracketGet(preview)

Get Bracket

The current bracket tournament, or None if none has been created yet.  Before &#x60;&#x60;reveal_at&#x60;&#x60;, player placements are withheld from the response (see &#x60;&#x60;_build_output_from_states&#x60;&#x60;) - only the roster and blank bracket shape are visible. &#x60;&#x60;preview&#x3D;true&#x60;&#x60; bypasses that gate, but only for a logged-in tournament admin; it\&#39;s a per-request opt-in (an admin\&#39;s own \&quot;peek early\&quot; button), not a way to reveal the bracket for everyone.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { GetBracketApiBracketGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  const body = {
    // boolean (optional)
    preview: true,
  } satisfies GetBracketApiBracketGetRequest;

  try {
    const data = await api.getBracketApiBracketGet(body);
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
| **preview** | `boolean` |  | [Optional] [Defaults to `false`] |

### Return type

[**BracketTournamentOutput**](BracketTournamentOutput.md)

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


## setBracketMatchApiBracketMatchIdPost

> BracketTournamentOutput setBracketMatchApiBracketMatchIdPost(matchId, setBracketMatchRequest)

Set Bracket Match

Update a match\&#39;s scheduled date / best-of / score (admin only).  PATCH semantics: only fields present in the request body change; omitted fields keep their stored values, and an explicit null clears a field.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { SetBracketMatchApiBracketMatchIdPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  const body = {
    // string
    matchId: matchId_example,
    // SetBracketMatchRequest
    setBracketMatchRequest: ...,
  } satisfies SetBracketMatchApiBracketMatchIdPostRequest;

  try {
    const data = await api.setBracketMatchApiBracketMatchIdPost(body);
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
| **matchId** | `string` |  | [Defaults to `undefined`] |
| **setBracketMatchRequest** | [SetBracketMatchRequest](SetBracketMatchRequest.md) |  | |

### Return type

[**BracketTournamentOutput**](BracketTournamentOutput.md)

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


## setBracketRevealAtApiBracketRevealAtPost

> BracketTournamentOutput setBracketRevealAtApiBracketRevealAtPost(setBracketRevealAtRequest)

Set Bracket Reveal At

Set (or clear, with null) when the bracket becomes publicly visible.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { SetBracketRevealAtApiBracketRevealAtPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  const body = {
    // SetBracketRevealAtRequest
    setBracketRevealAtRequest: ...,
  } satisfies SetBracketRevealAtApiBracketRevealAtPostRequest;

  try {
    const data = await api.setBracketRevealAtApiBracketRevealAtPost(body);
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
| **setBracketRevealAtRequest** | [SetBracketRevealAtRequest](SetBracketRevealAtRequest.md) |  | |

### Return type

[**BracketTournamentOutput**](BracketTournamentOutput.md)

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

