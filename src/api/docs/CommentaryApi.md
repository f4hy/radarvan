# CommentaryApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getMatchupCommentaryApiMatchupCommentaryPost**](CommentaryApi.md#getmatchupcommentaryapimatchupcommentarypost) | **POST** /api/matchup_commentary/ | Get Matchup Commentary |
| [**getMatchupCommentaryPromptPreviewApiMatchupCommentaryPromptPreviewGet**](CommentaryApi.md#getmatchupcommentarypromptpreviewapimatchupcommentarypromptpreviewget) | **GET** /api/matchup_commentary/prompt_preview | Get Matchup Commentary Prompt Preview |



## getMatchupCommentaryApiMatchupCommentaryPost

> MatchupCommentaryResponse getMatchupCommentaryApiMatchupCommentaryPost(matchupCommentaryRequest)

Get Matchup Commentary

Generate (or return the cached) pre-game hype commentary for a 1v1 matchup.  POST (not GET) and gated behind the write-tier API key deliberately - a cache miss triggers a real LLM call, not just a read. A cache hit is free and instant; see the module docstring for the caching scheme.  &#x60;&#x60;req.bypass_cache&#x60;&#x60; and &#x60;&#x60;req.force_refresh&#x60;&#x60; both skip the cache read and always call the LLM (still real, billed calls - not free just because caching is being bypassed). They differ in whether the result is then persisted: &#x60;&#x60;force_refresh&#x60;&#x60; overwrites the cached row, &#x60;&#x60;bypass_cache&#x60;&#x60; does not touch it. If both are set, &#x60;&#x60;bypass_cache&#x60;&#x60; wins (no write).

### Example

```ts
import {
  Configuration,
  CommentaryApi,
} from '';
import type { GetMatchupCommentaryApiMatchupCommentaryPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new CommentaryApi(config);

  const body = {
    // MatchupCommentaryRequest
    matchupCommentaryRequest: ...,
  } satisfies GetMatchupCommentaryApiMatchupCommentaryPostRequest;

  try {
    const data = await api.getMatchupCommentaryApiMatchupCommentaryPost(body);
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
| **matchupCommentaryRequest** | [MatchupCommentaryRequest](MatchupCommentaryRequest.md) |  | |

### Return type

[**MatchupCommentaryResponse**](MatchupCommentaryResponse.md)

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

