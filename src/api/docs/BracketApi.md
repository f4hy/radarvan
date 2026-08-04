# BracketApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createBracketApiBracketPost**](BracketApi.md#createbracketapibracketpost) | **POST** /api/bracket | Create Bracket |
| [**eligiblePlayersApiBracketEligiblePlayersGet**](BracketApi.md#eligibleplayersapibracketeligibleplayersget) | **GET** /api/bracket_eligible_players | Eligible Players |
| [**getBracketApiBracketGet**](BracketApi.md#getbracketapibracketget) | **GET** /api/bracket | Get Bracket |
| [**getBracketPredictionLeaderboardApiBracketPredictionLeaderboardGet**](BracketApi.md#getbracketpredictionleaderboardapibracketpredictionleaderboardget) | **GET** /api/bracket_prediction_leaderboard | Get Bracket Prediction Leaderboard |
| [**getBracketPredictionsApiBracketPredictionsGet**](BracketApi.md#getbracketpredictionsapibracketpredictionsget) | **GET** /api/bracket_predictions | Get Bracket Predictions |
| [**setBracketMatchApiBracketMatchIdPost**](BracketApi.md#setbracketmatchapibracketmatchidpost) | **POST** /api/bracket/{match_id} | Set Bracket Match |
| [**setBracketPredictionApiBracketPredictionsMatchIdPost**](BracketApi.md#setbracketpredictionapibracketpredictionsmatchidpost) | **POST** /api/bracket_predictions/{match_id} | Set Bracket Prediction |
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


## getBracketPredictionLeaderboardApiBracketPredictionLeaderboardGet

> Array&lt;BracketPredictionLeaderboardEntry&gt; getBracketPredictionLeaderboardApiBracketPredictionLeaderboardGet()

Get Bracket Prediction Leaderboard

Ranked \&quot;who\&#39;s called the most winners\&quot; standings for the active tournament - only counts predictions against matches that have completed, so an unfinished bracket\&#39;s leaderboard only grows, it never reshuffles into an incomplete-looking mid-guess state. Empty (not 404) before a tournament exists or before it\&#39;s revealed, same as &#x60;&#x60;get_bracket_predictions&#x60;&#x60;.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { GetBracketPredictionLeaderboardApiBracketPredictionLeaderboardGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  try {
    const data = await api.getBracketPredictionLeaderboardApiBracketPredictionLeaderboardGet();
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

[**Array&lt;BracketPredictionLeaderboardEntry&gt;**](BracketPredictionLeaderboardEntry.md)

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


## getBracketPredictionsApiBracketPredictionsGet

> Array&lt;BracketMatchPrediction&gt; getBracketPredictionsApiBracketPredictionsGet()

Get Bracket Predictions

Community \&quot;who wins this match\&quot; prediction tallies for every match with both players known - a hype feature, not authoritative (the real result lives in BracketMatchState via resolve_bracket). Reads are open; casting (POST) requires login. Withheld entirely before the bracket is revealed, same as player placements.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { GetBracketPredictionsApiBracketPredictionsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  try {
    const data = await api.getBracketPredictionsApiBracketPredictionsGet();
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

[**Array&lt;BracketMatchPrediction&gt;**](BracketMatchPrediction.md)

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


## setBracketMatchApiBracketMatchIdPost

> BracketTournamentOutput setBracketMatchApiBracketMatchIdPost(matchId, setBracketMatchRequest)

Set Bracket Match

Update a match\&#39;s scheduled date/time / best-of / score (admin only).  PATCH semantics: only fields present in the request body change; omitted fields keep their stored values, and an explicit null clears a field. &#x60;&#x60;scheduled_at&#x60;&#x60; can be set (or cleared) independently of best_of/scores - e.g. an admin scheduling a match ahead of time, before it\&#39;s been played.

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


## setBracketPredictionApiBracketPredictionsMatchIdPost

> BracketMatchPrediction setBracketPredictionApiBracketPredictionsMatchIdPost(matchId, setMatchPredictionRequest)

Set Bracket Prediction

Set (or clear, with null) the caller\&#39;s prediction for a match.

### Example

```ts
import {
  Configuration,
  BracketApi,
} from '';
import type { SetBracketPredictionApiBracketPredictionsMatchIdPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new BracketApi();

  const body = {
    // string
    matchId: matchId_example,
    // SetMatchPredictionRequest
    setMatchPredictionRequest: ...,
  } satisfies SetBracketPredictionApiBracketPredictionsMatchIdPostRequest;

  try {
    const data = await api.setBracketPredictionApiBracketPredictionsMatchIdPost(body);
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
| **setMatchPredictionRequest** | [SetMatchPredictionRequest](SetMatchPredictionRequest.md) |  | |

### Return type

[**BracketMatchPrediction**](BracketMatchPrediction.md)

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

