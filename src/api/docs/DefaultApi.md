# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**balanceTeamsApiBalanceTeamsGet**](DefaultApi.md#balanceteamsapibalanceteamsget) | **GET** /api/balance_teams/ | Balance Teams |
| [**generateTournamentReportApiGenerateTournamentReportTournamentNamePost**](DefaultApi.md#generatetournamentreportapigeneratetournamentreporttournamentnamepost) | **POST** /api/generate_tournament_report/{tournament_name} | Generate Tournament Report |
| [**getDatesApiDatesGet**](DefaultApi.md#getdatesapidatesget) | **GET** /api/dates/ | Get Dates |
| [**getFilesForMatchIdApiFilesForMatchGet**](DefaultApi.md#getfilesformatchidapifilesformatchget) | **GET** /api/files_for_match | Get Files For Match Id |
| [**getGeneralsStatsApiGeneralstatsGet**](DefaultApi.md#getgeneralsstatsapigeneralstatsget) | **GET** /api/generalstats | Get Generals Stats |
| [**getMatchByIdApiMatchMatchIdGet**](DefaultApi.md#getmatchbyidapimatchmatchidget) | **GET** /api/match/{match_id} | Get Match By Id |
| [**getMatchDetailsApiDetailsMatchIdGet**](DefaultApi.md#getmatchdetailsapidetailsmatchidget) | **GET** /api/details/{match_id} | Get Match Details |
| [**getMatchesApiMatchesMatchCountGet**](DefaultApi.md#getmatchesapimatchesmatchcountget) | **GET** /api/matches/{match_count} | Get Matches |
| [**getOverridesApiOverridesGet**](DefaultApi.md#getoverridesapioverridesget) | **GET** /api/overrides | Get Overrides |
| [**getPlayerRatingsApiPlayerRatingsGet**](DefaultApi.md#getplayerratingsapiplayerratingsget) | **GET** /api/player_ratings/ | Get Player Ratings |
| [**getPlayerStatsApiPlayerstatsGet**](DefaultApi.md#getplayerstatsapiplayerstatsget) | **GET** /api/playerstats | Get Player Stats |
| [**getTournamentReportApiTournamentReportTournamentNameGet**](DefaultApi.md#gettournamentreportapitournamentreporttournamentnameget) | **GET** /api/tournament_report/{tournament_name} | Get Tournament Report |
| [**getTournamentResultsApiTournamentResultsGet**](DefaultApi.md#gettournamentresultsapitournamentresultsget) | **GET** /api/tournament_results/ | Get Tournament Results |
| [**listFilesApiFilesGet**](DefaultApi.md#listfilesapifilesget) | **GET** /api/files/ | List Files |
| [**listReplaysApiReplaysGet**](DefaultApi.md#listreplaysapireplaysget) | **GET** /api/replays/ | List Replays |
| [**registerReplayUrlApiRegisterReplayUrlPost**](DefaultApi.md#registerreplayurlapiregisterreplayurlpost) | **POST** /api/register_replay_url | Register Replay Url |
| [**reparseApiReparseMatchIdPost**](DefaultApi.md#reparseapireparsematchidpost) | **POST** /api/reparse/{match_id} | Reparse |
| [**replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet**](DefaultApi.md#replayswithoutplayerstatsapireplayswithoutplayerstatsget) | **GET** /api/replays_without_playerstats/ | Replays Without Playerstats |
| [**repraseApiRepraseMatchIdPost**](DefaultApi.md#repraseapireprasematchidpost) | **POST** /api/reprase/{match_id} | Reprase |
| [**scrapeApiScrapeDaysPost**](DefaultApi.md#scrapeapiscrapedayspost) | **POST** /api/scrape/{days} | Scrape |
| [**setOverridesApiSetOverridePost**](DefaultApi.md#setoverridesapisetoverridepost) | **POST** /api/set_override/ | Set Overrides |
| [**testTournamentReportApiTestTournamentReportTournamentNamePost**](DefaultApi.md#testtournamentreportapitesttournamentreporttournamentnamepost) | **POST** /api/test_tournament_report/{tournament_name} | Test Tournament Report |
| [**updateNumTimestampsApiUpdateNumTimestampsPost**](DefaultApi.md#updatenumtimestampsapiupdatenumtimestampspost) | **POST** /api/update_num_timestamps/ | Update Num Timestamps |



## balanceTeamsApiBalanceTeamsGet

> any balanceTeamsApiBalanceTeamsGet(players)

Balance Teams

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { BalanceTeamsApiBalanceTeamsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // Array<PlayerEnum> (optional)
    players: ...,
  } satisfies BalanceTeamsApiBalanceTeamsGetRequest;

  try {
    const data = await api.balanceTeamsApiBalanceTeamsGet(body);
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
| **players** | `Array<PlayerEnum>` |  | [Optional] |

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


## generateTournamentReportApiGenerateTournamentReportTournamentNamePost

> string generateTournamentReportApiGenerateTournamentReportTournamentNamePost(tournamentName)

Generate Tournament Report

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GenerateTournamentReportApiGenerateTournamentReportTournamentNamePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    tournamentName: tournamentName_example,
  } satisfies GenerateTournamentReportApiGenerateTournamentReportTournamentNamePostRequest;

  try {
    const data = await api.generateTournamentReportApiGenerateTournamentReportTournamentNamePost(body);
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
| **tournamentName** | `string` |  | [Defaults to `undefined`] |

### Return type

**string**

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


## getDatesApiDatesGet

> any getDatesApiDatesGet()

Get Dates

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetDatesApiDatesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getDatesApiDatesGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getFilesForMatchIdApiFilesForMatchGet

> any getFilesForMatchIdApiFilesForMatchGet(matchId)

Get Files For Match Id

Get winner overrides.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetFilesForMatchIdApiFilesForMatchGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchId: 56,
  } satisfies GetFilesForMatchIdApiFilesForMatchGetRequest;

  try {
    const data = await api.getFilesForMatchIdApiFilesForMatchGet(body);
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


## getGeneralsStatsApiGeneralstatsGet

> GeneralStats getGeneralsStatsApiGeneralstatsGet()

Get Generals Stats

Get generals stats.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetGeneralsStatsApiGeneralstatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getGeneralsStatsApiGeneralstatsGet();
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

[**GeneralStats**](GeneralStats.md)

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


## getMatchByIdApiMatchMatchIdGet

> MatchInfo getMatchByIdApiMatchMatchIdGet(matchId)

Get Match By Id

Get listing of matches, up to a return count limit for paging.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchByIdApiMatchMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchId: 56,
  } satisfies GetMatchByIdApiMatchMatchIdGetRequest;

  try {
    const data = await api.getMatchByIdApiMatchMatchIdGet(body);
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

### Return type

[**MatchInfo**](MatchInfo.md)

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


## getMatchDetailsApiDetailsMatchIdGet

> MatchDetails getMatchDetailsApiDetailsMatchIdGet(matchId)

Get Match Details

Get details about a particular match

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchDetailsApiDetailsMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchId: 56,
  } satisfies GetMatchDetailsApiDetailsMatchIdGetRequest;

  try {
    const data = await api.getMatchDetailsApiDetailsMatchIdGet(body);
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

### Return type

[**MatchDetails**](MatchDetails.md)

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


## getMatchesApiMatchesMatchCountGet

> Matches getMatchesApiMatchesMatchCountGet(matchCount)

Get Matches

Get listing of matches, up to a return count limit for paging.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchesApiMatchesMatchCountGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchCount: 56,
  } satisfies GetMatchesApiMatchesMatchCountGetRequest;

  try {
    const data = await api.getMatchesApiMatchesMatchCountGet(body);
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
| **matchCount** | `number` |  | [Defaults to `undefined`] |

### Return type

[**Matches**](Matches.md)

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


## getOverridesApiOverridesGet

> Array&lt;WinnerOverride&gt; getOverridesApiOverridesGet()

Get Overrides

Get winner overrides.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetOverridesApiOverridesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getOverridesApiOverridesGet();
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

[**Array&lt;WinnerOverride&gt;**](WinnerOverride.md)

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


## getPlayerRatingsApiPlayerRatingsGet

> Array&lt;PlayerRatings&gt; getPlayerRatingsApiPlayerRatingsGet()

Get Player Ratings

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerRatingsApiPlayerRatingsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getPlayerRatingsApiPlayerRatingsGet();
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

[**Array&lt;PlayerRatings&gt;**](PlayerRatings.md)

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


## getPlayerStatsApiPlayerstatsGet

> PlayerStats getPlayerStatsApiPlayerstatsGet()

Get Player Stats

Get player stats.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerStatsApiPlayerstatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getPlayerStatsApiPlayerstatsGet();
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

[**PlayerStats**](PlayerStats.md)

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


## getTournamentReportApiTournamentReportTournamentNameGet

> TournamentReport getTournamentReportApiTournamentReportTournamentNameGet(tournamentName)

Get Tournament Report

Get listing of matches, up to a return count limit for paging.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetTournamentReportApiTournamentReportTournamentNameGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    tournamentName: tournamentName_example,
  } satisfies GetTournamentReportApiTournamentReportTournamentNameGetRequest;

  try {
    const data = await api.getTournamentReportApiTournamentReportTournamentNameGet(body);
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
| **tournamentName** | `string` |  | [Defaults to `undefined`] |

### Return type

[**TournamentReport**](TournamentReport.md)

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


## getTournamentResultsApiTournamentResultsGet

> Array&lt;TournamentResult&gt; getTournamentResultsApiTournamentResultsGet()

Get Tournament Results

Get listing of matches, up to a return count limit for paging.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetTournamentResultsApiTournamentResultsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getTournamentResultsApiTournamentResultsGet();
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

[**Array&lt;TournamentResult&gt;**](TournamentResult.md)

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


## listFilesApiFilesGet

> any listFilesApiFilesGet()

List Files

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ListFilesApiFilesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.listFilesApiFilesGet();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listReplaysApiReplaysGet

> Array&lt;GameRecord&gt; listReplaysApiReplaysGet()

List Replays

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ListReplaysApiReplaysGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.listReplaysApiReplaysGet();
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

[**Array&lt;GameRecord&gt;**](GameRecord.md)

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


## registerReplayUrlApiRegisterReplayUrlPost

> any registerReplayUrlApiRegisterReplayUrlPost(urlOfReplay)

Register Replay Url

Rerun the replay parser on this match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RegisterReplayUrlApiRegisterReplayUrlPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    urlOfReplay: urlOfReplay_example,
  } satisfies RegisterReplayUrlApiRegisterReplayUrlPostRequest;

  try {
    const data = await api.registerReplayUrlApiRegisterReplayUrlPost(body);
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
| **urlOfReplay** | `string` |  | [Defaults to `undefined`] |

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


## reparseApiReparseMatchIdPost

> any reparseApiReparseMatchIdPost(matchId)

Reparse

Rerun the replay parser on this match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ReparseApiReparseMatchIdPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchId: 56,
  } satisfies ReparseApiReparseMatchIdPostRequest;

  try {
    const data = await api.reparseApiReparseMatchIdPost(body);
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


## replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet

> any replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet(maxToReturn)

Replays Without Playerstats

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ReplaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number (optional)
    maxToReturn: 56,
  } satisfies ReplaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGetRequest;

  try {
    const data = await api.replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet(body);
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
| **maxToReturn** | `number` |  | [Optional] [Defaults to `10`] |

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


## repraseApiRepraseMatchIdPost

> any repraseApiRepraseMatchIdPost(matchId)

Reprase

Rerun the replay parser on this match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RepraseApiRepraseMatchIdPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchId: 56,
  } satisfies RepraseApiRepraseMatchIdPostRequest;

  try {
    const data = await api.repraseApiRepraseMatchIdPost(body);
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


## scrapeApiScrapeDaysPost

> any scrapeApiScrapeDaysPost(days)

Scrape

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ScrapeApiScrapeDaysPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    days: 56,
  } satisfies ScrapeApiScrapeDaysPostRequest;

  try {
    const data = await api.scrapeApiScrapeDaysPost(body);
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
| **days** | `number` |  | [Defaults to `undefined`] |

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


## setOverridesApiSetOverridePost

> WinnerOverride setOverridesApiSetOverridePost(matchId, winner)

Set Overrides

Set winner overrides.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { SetOverridesApiSetOverridePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    matchId: 56,
    // Team
    winner: ...,
  } satisfies SetOverridesApiSetOverridePostRequest;

  try {
    const data = await api.setOverridesApiSetOverridePost(body);
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
| **winner** | `Team` |  | [Defaults to `undefined`] [Enum: 0, 1, 2, 3, 4, -1] |

### Return type

[**WinnerOverride**](WinnerOverride.md)

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


## testTournamentReportApiTestTournamentReportTournamentNamePost

> TournamentReport testTournamentReportApiTestTournamentReportTournamentNamePost(tournamentName)

Test Tournament Report

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { TestTournamentReportApiTestTournamentReportTournamentNamePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    tournamentName: tournamentName_example,
  } satisfies TestTournamentReportApiTestTournamentReportTournamentNamePostRequest;

  try {
    const data = await api.testTournamentReportApiTestTournamentReportTournamentNamePost(body);
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
| **tournamentName** | `string` |  | [Defaults to `undefined`] |

### Return type

[**TournamentReport**](TournamentReport.md)

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


## updateNumTimestampsApiUpdateNumTimestampsPost

> any updateNumTimestampsApiUpdateNumTimestampsPost(maxToUpdate)

Update Num Timestamps

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { UpdateNumTimestampsApiUpdateNumTimestampsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies UpdateNumTimestampsApiUpdateNumTimestampsPostRequest;

  try {
    const data = await api.updateNumTimestampsApiUpdateNumTimestampsPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `1000`] |

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

