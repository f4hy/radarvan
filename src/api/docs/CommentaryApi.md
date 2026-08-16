# CommentaryApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getBracketSummaryApiBracketSummaryMatchIdGet**](CommentaryApi.md#getbracketsummaryapibracketsummarymatchidget) | **GET** /api/bracket_summary/{match_id} | Get Bracket Summary |
| [**getBracketSummaryPromptPreviewApiBracketSummaryPreviewMatchIdGet**](CommentaryApi.md#getbracketsummarypromptpreviewapibracketsummarypreviewmatchidget) | **GET** /api/bracket_summary_preview/{match_id} | Get Bracket Summary Prompt Preview |
| [**getMatchupCommentaryApiMatchupCommentaryGet**](CommentaryApi.md#getmatchupcommentaryapimatchupcommentaryget) | **GET** /api/matchup_commentary/ | Get Matchup Commentary |
| [**getMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGet**](CommentaryApi.md#getmatchupcommentarypromptpreviewapimatchupcommentarypromptpreviewget) | **GET** /api/matchup_commentary/prompt_preview | Get Matchup Commentary Prompt Preview |



## getBracketSummaryApiBracketSummaryMatchIdGet

> BracketSummaryResponse getBracketSummaryApiBracketSummaryMatchIdGet(matchId, bypassCache, forceRefresh)

Get Bracket Summary

Generate (or return the cached) post-game recap of one bracket set.  A GET, for the same reason the pre-game commentary route is one: the bracket UI shows this to everyone and a cache hit is free. A cache *miss* still triggers a real, billed LLM call, so the same two fences apply:  - The key is (tournament, bracket stage), both of which the server   resolves itself from &#x60;&#x60;match_id&#x60;&#x60; - a caller can\&#39;t mint fresh keys, and   &#x60;&#x60;_recappable_set&#x60;&#x60; refuses everything that isn\&#39;t a finished set with   all of its games on record. &#x60;&#x60;ready&#x3D;false&#x60;&#x60; is the \&quot;nothing to say yet\&quot;   answer, and costs nothing. - &#x60;&#x60;bypass_cache&#x60;&#x60;/&#x60;&#x60;force_refresh&#x60;&#x60; always call the LLM, so they need   the admin-tier key. They differ in whether the result is then   persisted: &#x60;&#x60;force_refresh&#x60;&#x60; overwrites the cached row, &#x60;&#x60;bypass_cache&#x60;&#x60;   does not touch it. If both are set, &#x60;&#x60;bypass_cache&#x60;&#x60; wins (no write).   &#x60;&#x60;force_refresh&#x60;&#x60; is the answer to a recap whose games an admin   relinked afterwards.

### Example

```ts
import {
  Configuration,
  CommentaryApi,
} from '';
import type { GetBracketSummaryApiBracketSummaryMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new CommentaryApi(config);

  const body = {
    // string
    matchId: matchId_example,
    // boolean (optional)
    bypassCache: true,
    // boolean (optional)
    forceRefresh: true,
  } satisfies GetBracketSummaryApiBracketSummaryMatchIdGetRequest;

  try {
    const data = await api.getBracketSummaryApiBracketSummaryMatchIdGet(body);
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
| **bypassCache** | `boolean` |  | [Optional] [Defaults to `false`] |
| **forceRefresh** | `boolean` |  | [Optional] [Defaults to `false`] |

### Return type

[**BracketSummaryResponse**](BracketSummaryResponse.md)

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


## getBracketSummaryPromptPreviewApiBracketSummaryPreviewMatchIdGet

> MatchupCommentaryPromptPreview getBracketSummaryPromptPreviewApiBracketSummaryPreviewMatchIdGet(matchId)

Get Bracket Summary Prompt Preview

Dev-only: assemble the exact system + user content that would be sent to the active LLM provider for this set\&#39;s recap, without calling the API.  A distinct top-level path rather than a sibling of &#x60;&#x60;/api/bracket_summary/{match_id}&#x60;&#x60; - the OpenAPI generator merges a static route with a parameterized sibling sharing its prefix (see CLAUDE.md).

### Example

```ts
import {
  Configuration,
  CommentaryApi,
} from '';
import type { GetBracketSummaryPromptPreviewApiBracketSummaryPreviewMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new CommentaryApi(config);

  const body = {
    // string
    matchId: matchId_example,
  } satisfies GetBracketSummaryPromptPreviewApiBracketSummaryPreviewMatchIdGetRequest;

  try {
    const data = await api.getBracketSummaryPromptPreviewApiBracketSummaryPreviewMatchIdGet(body);
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

### Return type

[**MatchupCommentaryPromptPreview**](MatchupCommentaryPromptPreview.md)

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


## getMatchupCommentaryApiMatchupCommentaryGet

> MatchupCommentaryResponse getMatchupCommentaryApiMatchupCommentaryGet(player1, player2, roundName, bypassCache, forceRefresh)

Get Matchup Commentary

Generate (or return the cached) pre-game hype commentary for a 1v1 matchup.  A GET so the normal-tier API key the browser ships with can reach it - the bracket UI needs to show this to everyone, and a cache hit is free and instant. A cache *miss* still triggers a real, billed LLM call, so the two things that would make that spend unbounded are fenced off:  - &#x60;&#x60;round_name&#x60;&#x60; must be one a bracket actually produces   (&#x60;&#x60;bracket.known_round_names()&#x60;&#x60;); the cache key is   (player1, player2, round_name) and all three must be enumerable, or a   caller could mint fresh keys forever. Player names are already bounded   by &#x60;&#x60;PlayerName&#x60;&#x60;\&#39;s alias resolution. - &#x60;&#x60;bypass_cache&#x60;&#x60;/&#x60;&#x60;force_refresh&#x60;&#x60; both skip the cache read and always   call the LLM, so they require the admin-tier key. They differ in   whether the result is then persisted: &#x60;&#x60;force_refresh&#x60;&#x60; overwrites the   cached row, &#x60;&#x60;bypass_cache&#x60;&#x60; does not touch it. If both are set,   &#x60;&#x60;bypass_cache&#x60;&#x60; wins (no write).

### Example

```ts
import {
  Configuration,
  CommentaryApi,
} from '';
import type { GetMatchupCommentaryApiMatchupCommentaryGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new CommentaryApi(config);

  const body = {
    // string
    player1: player1_example,
    // string
    player2: player2_example,
    // string
    roundName: roundName_example,
    // boolean (optional)
    bypassCache: true,
    // boolean (optional)
    forceRefresh: true,
  } satisfies GetMatchupCommentaryApiMatchupCommentaryGetRequest;

  try {
    const data = await api.getMatchupCommentaryApiMatchupCommentaryGet(body);
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
| **player1** | `string` |  | [Defaults to `undefined`] |
| **player2** | `string` |  | [Defaults to `undefined`] |
| **roundName** | `string` |  | [Defaults to `undefined`] |
| **bypassCache** | `boolean` |  | [Optional] [Defaults to `false`] |
| **forceRefresh** | `boolean` |  | [Optional] [Defaults to `false`] |

### Return type

[**MatchupCommentaryResponse**](MatchupCommentaryResponse.md)

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


## getMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGet

> MatchupCommentaryPromptPreview getMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGet(player1, player2, roundName)

Get Matchup Commentary Prompt Preview

Dev-only: assemble the exact system + user content that would be sent to the active LLM provider for this matchup, without calling the API - for inspecting and trimming payload size/cost. E.g.:      curl -s \&quot;http://localhost:8000/api/matchup_commentary/prompt_preview?player1&#x3D;X&amp;player2&#x3D;Y&amp;round_name&#x3D;Test\&quot; \\       | jq -r .userMessage &gt; /tmp/prompt.json

### Example

```ts
import {
  Configuration,
  CommentaryApi,
} from '';
import type { GetMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new CommentaryApi(config);

  const body = {
    // string
    player1: player1_example,
    // string
    player2: player2_example,
    // string
    roundName: roundName_example,
  } satisfies GetMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGetRequest;

  try {
    const data = await api.getMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGet(body);
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
| **player1** | `string` |  | [Defaults to `undefined`] |
| **player2** | `string` |  | [Defaults to `undefined`] |
| **roundName** | `string` |  | [Defaults to `undefined`] |

### Return type

[**MatchupCommentaryPromptPreview**](MatchupCommentaryPromptPreview.md)

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

