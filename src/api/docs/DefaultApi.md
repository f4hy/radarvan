# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**backfillMatchCompositionApiBackfillCompositionPost**](DefaultApi.md#backfillmatchcompositionapibackfillcompositionpost) | **POST** /api/backfill/composition | Backfill Match Composition |
| [**balanceTeamsApiBalanceTeamsGet**](DefaultApi.md#balanceteamsapibalanceteamsget) | **GET** /api/balance_teams/ | Balance Teams |
| [**computeMatchCompositionApiMatchesMatchIdCompositionPost**](DefaultApi.md#computematchcompositionapimatchesmatchidcompositionpost) | **POST** /api/matches/{match_id}/composition | Compute Match Composition |
| [**debugMatchApiDebugMatchMatchIdGet**](DefaultApi.md#debugmatchapidebugmatchmatchidget) | **GET** /api/debug/match/{match_id} | Debug Match |
| [**deleteOverrideApiOverrideMatchIdDelete**](DefaultApi.md#deleteoverrideapioverridematchiddelete) | **DELETE** /api/override/{match_id} | Delete Override |
| [**fetchMapForMatchApiFetchMapForMatchMatchIdPost**](DefaultApi.md#fetchmapformatchapifetchmapformatchmatchidpost) | **POST** /api/fetch_map_for_match/{match_id} | Fetch Map For Match |
| [**fetchMissingMapsApiFetchMissingMapsPost**](DefaultApi.md#fetchmissingmapsapifetchmissingmapspost) | **POST** /api/fetch_missing_maps | Fetch Missing Maps |
| [**fixIncompleteApiFixIncompletePost**](DefaultApi.md#fixincompleteapifixincompletepost) | **POST** /api/fix_incomplete/ | Fix Incomplete |
| [**fixUnkPlayersApiFixUnkPlayerPost**](DefaultApi.md#fixunkplayersapifixunkplayerpost) | **POST** /api/fix_unk_player/ | Fix Unk Players |
| [**generateTournamentReportApiGenerateTournamentReportTournamentNamePost**](DefaultApi.md#generatetournamentreportapigeneratetournamentreporttournamentnamepost) | **POST** /api/generate_tournament_report/{tournament_name} | Generate Tournament Report |
| [**getBuildOrdersApiBuildOrdersMatchIdGet**](DefaultApi.md#getbuildordersapibuildordersmatchidget) | **GET** /api/build_orders/{match_id} | Get Build Orders |
| [**getDatesApiDatesGet**](DefaultApi.md#getdatesapidatesget) | **GET** /api/dates/ | Get Dates |
| [**getFilesForMatchIdApiFilesForMatchGet**](DefaultApi.md#getfilesformatchidapifilesformatchget) | **GET** /api/files_for_match | Get Files For Match Id |
| [**getGeneralsStatsApiGeneralstatsGet**](DefaultApi.md#getgeneralsstatsapigeneralstatsget) | **GET** /api/generalstats | Get Generals Stats |
| [**getHeadToHeadApiPlayerRatingsHeadToHeadGet**](DefaultApi.md#getheadtoheadapiplayerratingsheadtoheadget) | **GET** /api/player_ratings/head_to_head/ | Get Head To Head |
| [**getMapDataApiMapDataMapNameGet**](DefaultApi.md#getmapdataapimapdatamapnameget) | **GET** /api/map_data/{map_name} | Get Map Data |
| [**getMapImageApiMapImageMapNameGet**](DefaultApi.md#getmapimageapimapimagemapnameget) | **GET** /api/map_image/{map_name} | Get Map Image |
| [**getMapMatchCountsApiMapMatchCountsGet**](DefaultApi.md#getmapmatchcountsapimapmatchcountsget) | **GET** /api/map_match_counts | Get Map Match Counts |
| [**getMapStatsApiMapStatsGet**](DefaultApi.md#getmapstatsapimapstatsget) | **GET** /api/map_stats/ | Get Map Stats |
| [**getMapSummaryApiMapSummaryPost**](DefaultApi.md#getmapsummaryapimapsummarypost) | **POST** /api/map_summary/ | Get Map Summary |
| [**getMapsByPlayerCountApiMapsByPlayerCountGet**](DefaultApi.md#getmapsbyplayercountapimapsbyplayercountget) | **GET** /api/maps_by_player_count | Get Maps By Player Count |
| [**getMatchByIdApiMatchMatchIdGet**](DefaultApi.md#getmatchbyidapimatchmatchidget) | **GET** /api/match/{match_id} | Get Match By Id |
| [**getMatchDetailsApiDetailsMatchIdGet**](DefaultApi.md#getmatchdetailsapidetailsmatchidget) | **GET** /api/details/{match_id} | Get Match Details |
| [**getMatchJsonUrlApiDebugJsonUrlMatchIdGet**](DefaultApi.md#getmatchjsonurlapidebugjsonurlmatchidget) | **GET** /api/debug/json_url/{match_id} | Get Match Json Url |
| [**getMatchReplayUrlApiReplayUrlMatchIdGet**](DefaultApi.md#getmatchreplayurlapireplayurlmatchidget) | **GET** /api/replay_url/{match_id} | Get Match Replay Url |
| [**getMatchesApiMatchesMatchCountGet**](DefaultApi.md#getmatchesapimatchesmatchcountget) | **GET** /api/matches/{match_count} | Get Matches |
| [**getMatchesByDateApiMatchesByDateDateGet**](DefaultApi.md#getmatchesbydateapimatchesbydatedateget) | **GET** /api/matches/by_date/{date} | Get Matches By Date |
| [**getOverridesApiOverridesGet**](DefaultApi.md#getoverridesapioverridesget) | **GET** /api/overrides | Get Overrides |
| [**getPlayerGameCountsApiPlayerGameCountsGet**](DefaultApi.md#getplayergamecountsapiplayergamecountsget) | **GET** /api/player_game_counts/ | Get Player Game Counts |
| [**getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet**](DefaultApi.md#getplayerratingdailychangesapiplayerratingsdailychangesget) | **GET** /api/player_ratings/daily_changes/ | Get Player Rating Daily Changes |
| [**getPlayerRatingsApiPlayerRatingsGet**](DefaultApi.md#getplayerratingsapiplayerratingsget) | **GET** /api/player_ratings/ | Get Player Ratings |
| [**getPlayerSkillsApiPlayerSkillsGet**](DefaultApi.md#getplayerskillsapiplayerskillsget) | **GET** /api/player_skills/ | Get Player Skills |
| [**getPlayerStatsApiPlayerstatsGet**](DefaultApi.md#getplayerstatsapiplayerstatsget) | **GET** /api/playerstats | Get Player Stats |
| [**getPlayerTeamGameCountsApiPlayerGameCountsTeamGet**](DefaultApi.md#getplayerteamgamecountsapiplayergamecountsteamget) | **GET** /api/player_game_counts/team/ | Get Player Team Game Counts |
| [**getPresignedForMatchIdApiPresignedUrlsForMatchGet**](DefaultApi.md#getpresignedformatchidapipresignedurlsformatchget) | **GET** /api/presigned_urls_for_match | Get Presigned For Match Id |
| [**getReplayByUrlApiReplayGet**](DefaultApi.md#getreplaybyurlapireplayget) | **GET** /api/replay | Get Replay By Url |
| [**getSuperlativesApiSuperlativesGet**](DefaultApi.md#getsuperlativesapisuperlativesget) | **GET** /api/superlatives | Get Superlatives |
| [**getTeamGamesWithoutWinnerApiTeamGamesWithoutWinnerGet**](DefaultApi.md#getteamgameswithoutwinnerapiteamgameswithoutwinnerget) | **GET** /api/team_games_without_winner/ | Get Team Games Without Winner |
| [**getTeamStatsApiTeamStatsGet**](DefaultApi.md#getteamstatsapiteamstatsget) | **GET** /api/team_stats/ | Get Team Stats |
| [**getTournamentReportApiTournamentReportTournamentNameGet**](DefaultApi.md#gettournamentreportapitournamentreporttournamentnameget) | **GET** /api/tournament_report/{tournament_name} | Get Tournament Report |
| [**getTournamentResultsApiTournamentResultsGet**](DefaultApi.md#gettournamentresultsapitournamentresultsget) | **GET** /api/tournament_results/ | Get Tournament Results |
| [**isTournamentGameApiIsTournamentGameMatchIdGet**](DefaultApi.md#istournamentgameapiistournamentgamematchidget) | **GET** /api/is_tournament_game/{match_id} | Is Tournament Game |
| [**listFilesApiFilesGet**](DefaultApi.md#listfilesapifilesget) | **GET** /api/files/ | List Files |
| [**listMissingMapsEndpointApiMissingMapsGet**](DefaultApi.md#listmissingmapsendpointapimissingmapsget) | **GET** /api/missing_maps | List Missing Maps Endpoint |
| [**listPendingUnprocessedApiFilesPendingUnprocessedGet**](DefaultApi.md#listpendingunprocessedapifilespendingunprocessedget) | **GET** /api/files/pending_unprocessed | List Pending Unprocessed |
| [**listReplaysApiReplaysGet**](DefaultApi.md#listreplaysapireplaysget) | **GET** /api/replays/ | List Replays |
| [**partitionTeamsApiPartitionTeamsTeamSizeGet**](DefaultApi.md#partitionteamsapipartitionteamsteamsizeget) | **GET** /api/partition_teams/{team_size} | Partition Teams |
| [**randomizeDraftApiDraftRandomizePost**](DefaultApi.md#randomizedraftapidraftrandomizepost) | **POST** /api/draft/randomize | Randomize Draft |
| [**recomputeSuperlativesApiSuperlativesRecomputePost**](DefaultApi.md#recomputesuperlativesapisuperlativesrecomputepost) | **POST** /api/superlatives/recompute | Recompute Superlatives |
| [**refreshMatchesFromJsonApiRefreshMatchesFromJsonPost**](DefaultApi.md#refreshmatchesfromjsonapirefreshmatchesfromjsonpost) | **POST** /api/refresh_matches_from_json/ | Refresh Matches From Json |
| [**registerMatchesApiRegisterMatchesPost**](DefaultApi.md#registermatchesapiregistermatchespost) | **POST** /api/register_matches/ | Register Matches |
| [**registerReplayUrlApiRegisterReplayUrlPost**](DefaultApi.md#registerreplayurlapiregisterreplayurlpost) | **POST** /api/register_replay_url | Register Replay Url |
| [**renderMapWithPlayersApiMapRenderPost**](DefaultApi.md#rendermapwithplayersapimaprenderpost) | **POST** /api/map_render | Render Map With Players |
| [**reparseApiReparseMatchIdPost**](DefaultApi.md#reparseapireparsematchidpost) | **POST** /api/reparse/{match_id} | Reparse |
| [**reparseBeforeDateApiReparseBeforeDatePost**](DefaultApi.md#reparsebeforedateapireparsebeforedatepost) | **POST** /api/reparse_before_date/ | Reparse Before Date |
| [**reparseNonV2ApiReparseNonV2Post**](DefaultApi.md#reparsenonv2apireparsenonv2post) | **POST** /api/reparse_non_v2/ | Reparse Non V2 |
| [**reparseRecentApiReparseRecentPost**](DefaultApi.md#reparserecentapireparserecentpost) | **POST** /api/reparse_recent/ | Reparse Recent |
| [**replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet**](DefaultApi.md#replayswithoutplayerstatsapireplayswithoutplayerstatsget) | **GET** /api/replays_without_playerstats/ | Replays Without Playerstats |
| [**resetMatchApiMatchMatchIdDelete**](DefaultApi.md#resetmatchapimatchmatchiddelete) | **DELETE** /api/match/{match_id} | Reset Match |
| [**saveMapDataApiMapDataMapNamePost**](DefaultApi.md#savemapdataapimapdatamapnamepost) | **POST** /api/map_data/{map_name} | Save Map Data |
| [**scrapeApiScrapeDaysPost**](DefaultApi.md#scrapeapiscrapedayspost) | **POST** /api/scrape/{days} | Scrape |
| [**setOverrideApiSetOverridePost**](DefaultApi.md#setoverrideapisetoverridepost) | **POST** /api/set_override/ | Set Override |
| [**testTournamentReportApiTestTournamentReportTournamentNamePost**](DefaultApi.md#testtournamentreportapitesttournamentreporttournamentnamepost) | **POST** /api/test_tournament_report/{tournament_name} | Test Tournament Report |
| [**updateMatchesMissingDataApiUpdateMatchesMissingDataPost**](DefaultApi.md#updatematchesmissingdataapiupdatematchesmissingdatapost) | **POST** /api/update_matches_missing_data/ | Update Matches Missing Data |
| [**uploadReplayApiUploadReplayPost**](DefaultApi.md#uploadreplayapiuploadreplaypost) | **POST** /api/upload_replay | Upload Replay |



## backfillMatchCompositionApiBackfillCompositionPost

> number backfillMatchCompositionApiBackfillCompositionPost()

Backfill Match Composition

Backfill and persist the composition for a match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { BackfillMatchCompositionApiBackfillCompositionPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.backfillMatchCompositionApiBackfillCompositionPost();
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

**number**

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


## balanceTeamsApiBalanceTeamsGet

> { [key: string]: number; } balanceTeamsApiBalanceTeamsGet(players)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // Array<string> (optional)
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
| **players** | `Array<string>` |  | [Optional] |

### Return type

**{ [key: string]: number; }**

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


## computeMatchCompositionApiMatchesMatchIdCompositionPost

> GameComposition computeMatchCompositionApiMatchesMatchIdCompositionPost(matchId)

Compute Match Composition

Compute and persist the composition (teams, humans vs CPUs, category) for a match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ComputeMatchCompositionApiMatchesMatchIdCompositionPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies ComputeMatchCompositionApiMatchesMatchIdCompositionPostRequest;

  try {
    const data = await api.computeMatchCompositionApiMatchesMatchIdCompositionPost(body);
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

[**GameComposition**](GameComposition.md)

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


## debugMatchApiDebugMatchMatchIdGet

> { [key: string]: any; } debugMatchApiDebugMatchMatchIdGet(matchId)

Debug Match

Return every row related to a match_id across all tables, keyed by table name.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { DebugMatchApiDebugMatchMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies DebugMatchApiDebugMatchMatchIdGetRequest;

  try {
    const data = await api.debugMatchApiDebugMatchMatchIdGet(body);
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

**{ [key: string]: any; }**

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


## deleteOverrideApiOverrideMatchIdDelete

> { [key: string]: string | null; } deleteOverrideApiOverrideMatchIdDelete(matchId)

Delete Override

Delete a winner override for a match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { DeleteOverrideApiOverrideMatchIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies DeleteOverrideApiOverrideMatchIdDeleteRequest;

  try {
    const data = await api.deleteOverrideApiOverrideMatchIdDelete(body);
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
  DefaultApi,
} from '';
import type { FetchMapForMatchApiFetchMapForMatchMatchIdPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## fetchMissingMapsApiFetchMissingMapsPost

> FetchMissingMapsResponse fetchMissingMapsApiFetchMissingMapsPost(maxToUpdate, parseMap)

Fetch Missing Maps

Pull up to &#x60;max_to_update&#x60; missing maps from cncstats and upload to S3.  When &#x60;parse_map&#x60; is true and the local mapparse binary is available, the .map file is also parsed and saved to MapData.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { FetchMissingMapsApiFetchMissingMapsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
    // boolean (optional)
    parseMap: true,
  } satisfies FetchMissingMapsApiFetchMissingMapsPostRequest;

  try {
    const data = await api.fetchMissingMapsApiFetchMissingMapsPost(body);
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
| **parseMap** | `boolean` |  | [Optional] [Defaults to `true`] |

### Return type

[**FetchMissingMapsResponse**](FetchMissingMapsResponse.md)

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


## fixIncompleteApiFixIncompletePost

> { [key: string]: number | null; } fixIncompleteApiFixIncompletePost(maxToUpdate)

Fix Incomplete

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { FixIncompleteApiFixIncompletePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies FixIncompleteApiFixIncompletePostRequest;

  try {
    const data = await api.fixIncompleteApiFixIncompletePost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `1`] |

### Return type

**{ [key: string]: number | null; }**

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


## fixUnkPlayersApiFixUnkPlayerPost

> { [key: string]: number | null; } fixUnkPlayersApiFixUnkPlayerPost(maxToUpdate)

Fix Unk Players

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { FixUnkPlayersApiFixUnkPlayerPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies FixUnkPlayersApiFixUnkPlayerPostRequest;

  try {
    const data = await api.fixUnkPlayersApiFixUnkPlayerPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `1`] |

### Return type

**{ [key: string]: number | null; }**

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## getBuildOrdersApiBuildOrdersMatchIdGet

> { [key: string]: BuildOrder; } getBuildOrdersApiBuildOrdersMatchIdGet(matchId)

Get Build Orders

Per-player build orders for a match (the same data the match details page shows).  Keyed by player name; each value has the player\&#39;s first-10 buildings, units, and upgrades in chronological order. Projected from the cached MatchDetails (see cache.details_from_id), so it shares the durable, versioned details cache and runs no extra computation. An unparsed match returns {} uncached so it picks up data once processed.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetBuildOrdersApiBuildOrdersMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies GetBuildOrdersApiBuildOrdersMatchIdGetRequest;

  try {
    const data = await api.getBuildOrdersApiBuildOrdersMatchIdGet(body);
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

[**{ [key: string]: BuildOrder; }**](BuildOrder.md)

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


## getDatesApiDatesGet

> { [key: string]: number; } getDatesApiDatesGet()

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

**{ [key: string]: number; }**

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


## getFilesForMatchIdApiFilesForMatchGet

> { [key: string]: ResponseGetFilesForMatchIdApiFilesForMatchGetValue; } getFilesForMatchIdApiFilesForMatchGet(matchId)

Get Files For Match Id

Get all replay and parsed files for a match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetFilesForMatchIdApiFilesForMatchGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

[**{ [key: string]: ResponseGetFilesForMatchIdApiFilesForMatchGetValue; }**](ResponseGetFilesForMatchIdApiFilesForMatchGetValue.md)

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


## getGeneralsStatsApiGeneralstatsGet

> GeneralStats getGeneralsStatsApiGeneralstatsGet(gameFormat)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetGeneralsStatsApiGeneralstatsGetRequest;

  try {
    const data = await api.getGeneralsStatsApiGeneralstatsGet(body);
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
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**GeneralStats**](GeneralStats.md)

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


## getHeadToHeadApiPlayerRatingsHeadToHeadGet

> { [key: string]: { [key: string]: HeadToHead; }; } getHeadToHeadApiPlayerRatingsHeadToHeadGet(gameFormat)

Get Head To Head

Win/loss record for every rated player against every other rated player.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetHeadToHeadApiPlayerRatingsHeadToHeadGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string (optional)
    gameFormat: gameFormat_example,
  } satisfies GetHeadToHeadApiPlayerRatingsHeadToHeadGetRequest;

  try {
    const data = await api.getHeadToHeadApiPlayerRatingsHeadToHeadGet(body);
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
| **gameFormat** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

**{ [key: string]: { [key: string]: HeadToHead; }; }**

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
  DefaultApi,
} from '';
import type { GetMapDataApiMapDataMapNameGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

Return the WebP for a map, preferring S3 (dynamic) over public/maps (legacy).  Strips a trailing &#x60;.map&#x60; extension and tries case-insensitive variants in S3. Falls back to the bundled &#x60;dist/maps/&lt;name&gt;.webp&#x60; for legacy maps that haven\&#39;t been migrated yet.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMapImageApiMapImageMapNameGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

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
  DefaultApi,
} from '';
import type { GetMapMatchCountsApiMapMatchCountsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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
  DefaultApi,
} from '';
import type { GetMapStatsApiMapStatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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
  DefaultApi,
} from '';
import type { GetMapSummaryApiMapSummaryPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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
  DefaultApi,
} from '';
import type { GetMapsByPlayerCountApiMapsByPlayerCountGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## getMatchByIdApiMatchMatchIdGet

> MatchInfo getMatchByIdApiMatchMatchIdGet(matchId)

Get Match By Id

Get a single match by its ID.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchByIdApiMatchMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## getMatchDetailsApiDetailsMatchIdGet

> MatchDetails getMatchDetailsApiDetailsMatchIdGet(matchId)

Get Match Details

Get details about a particular match.  Result is cached in-process (see cache.details_from_id, invalidated on reparse/upload). Existing details are immutable until reparse, so we also let the browser cache them; an unparsed match returns empty and is not cached so it picks up data once processed.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchDetailsApiDetailsMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## getMatchJsonUrlApiDebugJsonUrlMatchIdGet

> { [key: string]: string | null; } getMatchJsonUrlApiDebugJsonUrlMatchIdGet(matchId)

Get Match Json Url

Return a presigned S3 URL for the parsed JSON of a match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchJsonUrlApiDebugJsonUrlMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies GetMatchJsonUrlApiDebugJsonUrlMatchIdGetRequest;

  try {
    const data = await api.getMatchJsonUrlApiDebugJsonUrlMatchIdGet(body);
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


## getMatchReplayUrlApiReplayUrlMatchIdGet

> { [key: string]: string | null; } getMatchReplayUrlApiReplayUrlMatchIdGet(matchId)

Get Match Replay Url

Return a presigned S3 URL for the .rep file of a match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchReplayUrlApiReplayUrlMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies GetMatchReplayUrlApiReplayUrlMatchIdGetRequest;

  try {
    const data = await api.getMatchReplayUrlApiReplayUrlMatchIdGet(body);
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


## getMatchesApiMatchesMatchCountGet

> Matches getMatchesApiMatchesMatchCountGet(matchCount, excludeDev)

Get Matches

Get listing of matches, up to a return count limit for paging.  When exclude_dev is set, matches sourced from a \&quot;dev-\&quot; zulu build are omitted.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchesApiMatchesMatchCountGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchCount: 56,
    // boolean (optional)
    excludeDev: true,
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
| **excludeDev** | `boolean` |  | [Optional] [Defaults to `false`] |

### Return type

[**Matches**](Matches.md)

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


## getMatchesByDateApiMatchesByDateDateGet

> Matches getMatchesByDateApiMatchesByDateDateGet(date, excludeDev)

Get Matches By Date

Get all matches for a specific date.  When exclude_dev is set, matches sourced from a \&quot;dev-\&quot; zulu build are omitted.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchesByDateApiMatchesByDateDateGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // Date
    date: 2013-10-20,
    // boolean (optional)
    excludeDev: true,
  } satisfies GetMatchesByDateApiMatchesByDateDateGetRequest;

  try {
    const data = await api.getMatchesByDateApiMatchesByDateDateGet(body);
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
| **date** | `Date` |  | [Defaults to `undefined`] |
| **excludeDev** | `boolean` |  | [Optional] [Defaults to `false`] |

### Return type

[**Matches**](Matches.md)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getPlayerGameCountsApiPlayerGameCountsGet

> Array&lt;PlayerGameCount&gt; getPlayerGameCountsApiPlayerGameCountsGet()

Get Player Game Counts

Get all player names with their total game count, sorted by count descending.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerGameCountsApiPlayerGameCountsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getPlayerGameCountsApiPlayerGameCountsGet();
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

[**Array&lt;PlayerGameCount&gt;**](PlayerGameCount.md)

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


## getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet

> Array&lt;PlayerRatingDailyChange&gt; getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet(forDate)

Get Player Rating Daily Changes

Return each player\&#39;s ordinal rating change for the given date.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // Date
    forDate: 2013-10-20,
  } satisfies GetPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGetRequest;

  try {
    const data = await api.getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet(body);
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
| **forDate** | `Date` |  | [Defaults to `undefined`] |

### Return type

[**Array&lt;PlayerRatingDailyChange&gt;**](PlayerRatingDailyChange.md)

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


## getPlayerRatingsApiPlayerRatingsGet

> PlayerRatingData getPlayerRatingsApiPlayerRatingsGet(gameFormat)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string | Filter by game format: 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetPlayerRatingsApiPlayerRatingsGetRequest;

  try {
    const data = await api.getPlayerRatingsApiPlayerRatingsGet(body);
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
| **gameFormat** | `string` | Filter by game format: 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**PlayerRatingData**](PlayerRatingData.md)

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


## getPlayerSkillsApiPlayerSkillsGet

> Array&lt;PlayerSkill&gt; getPlayerSkillsApiPlayerSkillsGet(gameFormat)

Get Player Skills

Alternative skill estimate via Whole-History Rating (Coulom 2008).  Each player\&#39;s skill is a function of time (one rating per date played) with a Gaussian random-walk prior on changes; team Bradley-Terry likelihood for outcomes. Returns each player\&#39;s rating at their most recent game, mean-centered across players.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerSkillsApiPlayerSkillsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetPlayerSkillsApiPlayerSkillsGetRequest;

  try {
    const data = await api.getPlayerSkillsApiPlayerSkillsGet(body);
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
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;PlayerSkill&gt;**](PlayerSkill.md)

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


## getPlayerStatsApiPlayerstatsGet

> PlayerStats getPlayerStatsApiPlayerstatsGet(gameFormat)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetPlayerStatsApiPlayerstatsGetRequest;

  try {
    const data = await api.getPlayerStatsApiPlayerstatsGet(body);
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
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**PlayerStats**](PlayerStats.md)

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


## getPlayerTeamGameCountsApiPlayerGameCountsTeamGet

> Array&lt;PlayerGameCount&gt; getPlayerTeamGameCountsApiPlayerGameCountsTeamGet()

Get Player Team Game Counts

Get player names with their total team game count, sorted by count descending.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerTeamGameCountsApiPlayerGameCountsTeamGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getPlayerTeamGameCountsApiPlayerGameCountsTeamGet();
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

[**Array&lt;PlayerGameCount&gt;**](PlayerGameCount.md)

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


## getPresignedForMatchIdApiPresignedUrlsForMatchGet

> { [key: string]: string | null; } getPresignedForMatchIdApiPresignedUrlsForMatchGet(matchId)

Get Presigned For Match Id

Get presigned urls for all files for a match id.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPresignedForMatchIdApiPresignedUrlsForMatchGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies GetPresignedForMatchIdApiPresignedUrlsForMatchGetRequest;

  try {
    const data = await api.getPresignedForMatchIdApiPresignedUrlsForMatchGet(body);
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


## getReplayByUrlApiReplayGet

> { [key: string]: string | null; } getReplayByUrlApiReplayGet(urlOfReplay)

Get Replay By Url

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetReplayByUrlApiReplayGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string
    urlOfReplay: urlOfReplay_example,
  } satisfies GetReplayByUrlApiReplayGetRequest;

  try {
    const data = await api.getReplayByUrlApiReplayGet(body);
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


## getSuperlativesApiSuperlativesGet

> Superlatives getSuperlativesApiSuperlativesGet()

Get Superlatives

Serve superlatives from the DB if available, otherwise compute on the fly.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetSuperlativesApiSuperlativesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getSuperlativesApiSuperlativesGet();
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

[**Superlatives**](Superlatives.md)

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


## getTeamGamesWithoutWinnerApiTeamGamesWithoutWinnerGet

> Array&lt;{ [key: string]: any; }&gt; getTeamGamesWithoutWinnerApiTeamGamesWithoutWinnerGet()

Get Team Games Without Winner

Return match IDs and dates for team games with no winner (winning_team&#x3D;0).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetTeamGamesWithoutWinnerApiTeamGamesWithoutWinnerGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getTeamGamesWithoutWinnerApiTeamGamesWithoutWinnerGet();
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

**Array<{ [key: string]: any; }>**

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


## getTeamStatsApiTeamStatsGet

> TeamStatsResponse getTeamStatsApiTeamStatsGet()

Get Team Stats

Get win/loss records grouped by team composition, for teams with &gt;5 games.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetTeamStatsApiTeamStatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getTeamStatsApiTeamStatsGet();
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

[**TeamStatsResponse**](TeamStatsResponse.md)

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


## getTournamentReportApiTournamentReportTournamentNameGet

> TournamentReport getTournamentReportApiTournamentReportTournamentNameGet(tournamentName)

Get Tournament Report

Get report for a specific tournament.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetTournamentReportApiTournamentReportTournamentNameGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## getTournamentResultsApiTournamentResultsGet

> Array&lt;TournamentResult&gt; getTournamentResultsApiTournamentResultsGet()

Get Tournament Results

Get results for all tournaments.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetTournamentResultsApiTournamentResultsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## isTournamentGameApiIsTournamentGameMatchIdGet

> string isTournamentGameApiIsTournamentGameMatchIdGet(matchId)

Is Tournament Game

test if a match is a tournament game.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { IsTournamentGameApiIsTournamentGameMatchIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies IsTournamentGameApiIsTournamentGameMatchIdGetRequest;

  try {
    const data = await api.isTournamentGameApiIsTournamentGameMatchIdGet(body);
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

**string**

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


## listFilesApiFilesGet

> Array&lt;ReplayFileSchema&gt; listFilesApiFilesGet()

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

[**Array&lt;ReplayFileSchema&gt;**](ReplayFileSchema.md)

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
  DefaultApi,
} from '';
import type { ListMissingMapsEndpointApiMissingMapsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## listPendingUnprocessedApiFilesPendingUnprocessedGet

> Array&lt;ReplayFileSchema&gt; listPendingUnprocessedApiFilesPendingUnprocessedGet()

List Pending Unprocessed

Return replay files that are pending but have no parsed JSON.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ListPendingUnprocessedApiFilesPendingUnprocessedGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.listPendingUnprocessedApiFilesPendingUnprocessedGet();
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

[**Array&lt;ReplayFileSchema&gt;**](ReplayFileSchema.md)

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


## listReplaysApiReplaysGet

> Array&lt;GameRecord&gt; listReplaysApiReplaysGet(matchId, gameDate)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    matchId: 56,
    // Date (optional)
    gameDate: 2013-10-20,
  } satisfies ListReplaysApiReplaysGetRequest;

  try {
    const data = await api.listReplaysApiReplaysGet(body);
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
| **matchId** | `number` |  | [Optional] [Defaults to `undefined`] |
| **gameDate** | `Date` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;GameRecord&gt;**](GameRecord.md)

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


## partitionTeamsApiPartitionTeamsTeamSizeGet

> Array&lt;Array&lt;string | null&gt;&gt; partitionTeamsApiPartitionTeamsTeamSizeGet(teamSize, players)

Partition Teams

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PartitionTeamsApiPartitionTeamsTeamSizeGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    teamSize: 56,
    // Array<PlayerEnum> (optional)
    players: ...,
  } satisfies PartitionTeamsApiPartitionTeamsTeamSizeGetRequest;

  try {
    const data = await api.partitionTeamsApiPartitionTeamsTeamSizeGet(body);
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
| **teamSize** | `number` |  | [Defaults to `undefined`] |
| **players** | `Array<PlayerEnum>` |  | [Optional] |

### Return type

**Array<Array<string | null>>**

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


## randomizeDraftApiDraftRandomizePost

> DraftResult randomizeDraftApiDraftRandomizePost(draftRequest)

Randomize Draft

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RandomizeDraftApiDraftRandomizePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // DraftRequest
    draftRequest: ...,
  } satisfies RandomizeDraftApiDraftRandomizePostRequest;

  try {
    const data = await api.randomizeDraftApiDraftRandomizePost(body);
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
| **draftRequest** | [DraftRequest](DraftRequest.md) |  | |

### Return type

[**DraftResult**](DraftResult.md)

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


## recomputeSuperlativesApiSuperlativesRecomputePost

> { [key: string]: string | null; } recomputeSuperlativesApiSuperlativesRecomputePost()

Recompute Superlatives

Trigger superlatives recompute in the background and return immediately.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RecomputeSuperlativesApiSuperlativesRecomputePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.recomputeSuperlativesApiSuperlativesRecomputePost();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## refreshMatchesFromJsonApiRefreshMatchesFromJsonPost

> { [key: string]: number | null; } refreshMatchesFromJsonApiRefreshMatchesFromJsonPost(maxToUpdate)

Refresh Matches From Json

Re-parse existing JSON files from S3 and update DB matches if they differ.  Does NOT re-run cncstats — only reloads the already-parsed JSON from S3. Phase 1 (S3 fetches) runs in parallel; Phase 2 (DB writes) runs serially. Fetches up to max_to_update * 4 candidates to account for non-differing matches.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RefreshMatchesFromJsonApiRefreshMatchesFromJsonPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies RefreshMatchesFromJsonApiRefreshMatchesFromJsonPostRequest;

  try {
    const data = await api.refreshMatchesFromJsonApiRefreshMatchesFromJsonPost(body);
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

**{ [key: string]: number | null; }**

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


## registerMatchesApiRegisterMatchesPost

> { [key: string]: string | null; } registerMatchesApiRegisterMatchesPost()

Register Matches

Register Match rows for any ParsedReplayJson that has no corresponding Match.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RegisterMatchesApiRegisterMatchesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.registerMatchesApiRegisterMatchesPost();
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

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## registerReplayUrlApiRegisterReplayUrlPost

> MatchInfo registerReplayUrlApiRegisterReplayUrlPost(urlOfReplay)

Register Replay Url

Register and parse a new replay from a URL.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RegisterReplayUrlApiRegisterReplayUrlPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

[**MatchInfo**](MatchInfo.md)

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
  DefaultApi,
} from '';
import type { RenderMapWithPlayersApiMapRenderPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## reparseApiReparseMatchIdPost

> MatchInfo reparseApiReparseMatchIdPost(matchId)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

[**MatchInfo**](MatchInfo.md)

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


## reparseBeforeDateApiReparseBeforeDatePost

> { [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; } reparseBeforeDateApiReparseBeforeDatePost(before, maxToUpdate)

Reparse Before Date

Re-run cncstats on matches whose parsed JSON was last updated before &#x60;before&#x60;.  Calls cncstats for each match — slower than refresh_matches_from_json but picks up new fields added to the parser output.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ReparseBeforeDateApiReparseBeforeDatePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // Date
    before: 2013-10-20,
    // number (optional)
    maxToUpdate: 56,
  } satisfies ReparseBeforeDateApiReparseBeforeDatePostRequest;

  try {
    const data = await api.reparseBeforeDateApiReparseBeforeDatePost(body);
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
| **before** | `Date` |  | [Defaults to `undefined`] |
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `10`] |

### Return type

[**{ [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; }**](ResponseReparseBeforeDateApiReparseBeforeDatePostValue.md)

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


## reparseNonV2ApiReparseNonV2Post

> { [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; } reparseNonV2ApiReparseNonV2Post(maxToUpdate, maxConcurrent)

Reparse Non V2

Re-run cncstats on matches whose parsed JSON was last updated before &#x60;before&#x60;.  Calls cncstats for each match — slower than refresh_matches_from_json but picks up new fields added to the parser output.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ReparseNonV2ApiReparseNonV2PostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
    // number (optional)
    maxConcurrent: 56,
  } satisfies ReparseNonV2ApiReparseNonV2PostRequest;

  try {
    const data = await api.reparseNonV2ApiReparseNonV2Post(body);
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
| **maxConcurrent** | `number` |  | [Optional] [Defaults to `8`] |

### Return type

[**{ [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; }**](ResponseReparseBeforeDateApiReparseBeforeDatePostValue.md)

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


## reparseRecentApiReparseRecentPost

> { [key: string]: ResponseReparseRecentApiReparseRecentPostValue; } reparseRecentApiReparseRecentPost(days)

Reparse Recent

Re-run cncstats on all matches whose game_date is within the last &#x60;days&#x60; days.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ReparseRecentApiReparseRecentPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    days: 56,
  } satisfies ReparseRecentApiReparseRecentPostRequest;

  try {
    const data = await api.reparseRecentApiReparseRecentPost(body);
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
| **days** | `number` |  | [Optional] [Defaults to `3`] |

### Return type

[**{ [key: string]: ResponseReparseRecentApiReparseRecentPostValue; }**](ResponseReparseRecentApiReparseRecentPostValue.md)

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


## replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet

> Array&lt;{ [key: string]: any; }&gt; replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet(maxToReturn)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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

**Array<{ [key: string]: any; }>**

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


## resetMatchApiMatchMatchIdDelete

> { [key: string]: number | null; } resetMatchApiMatchMatchIdDelete(matchId)

Reset Match

Delete all parsed data for a match and reset its ReplayFile(s) to pending.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ResetMatchApiMatchMatchIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
  } satisfies ResetMatchApiMatchMatchIdDeleteRequest;

  try {
    const data = await api.resetMatchApiMatchMatchIdDelete(body);
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

**{ [key: string]: number | null; }**

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
  DefaultApi,
} from '';
import type { SaveMapDataApiMapDataMapNamePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## scrapeApiScrapeDaysPost

> { [key: string]: string | null; } scrapeApiScrapeDaysPost(days)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## setOverrideApiSetOverridePost

> WinnerOverride setOverrideApiSetOverridePost(matchId, winner, incomplete)

Set Override

Set a winner and/or incomplete override for a match. Persists through re-parses.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { SetOverrideApiSetOverridePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number
    matchId: 56,
    // Team (optional)
    winner: ...,
    // string (optional)
    incomplete: incomplete_example,
  } satisfies SetOverrideApiSetOverridePostRequest;

  try {
    const data = await api.setOverrideApiSetOverridePost(body);
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
| **winner** | `Team` |  | [Optional] [Defaults to `undefined`] [Enum: 0, 1, 2, 3, 4, -1] |
| **incomplete** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**WinnerOverride**](WinnerOverride.md)

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
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

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


## updateMatchesMissingDataApiUpdateMatchesMissingDataPost

> { [key: string]: number | null; } updateMatchesMissingDataApiUpdateMatchesMissingDataPost(maxToUpdate)

Update Matches Missing Data

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { UpdateMatchesMissingDataApiUpdateMatchesMissingDataPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies UpdateMatchesMissingDataApiUpdateMatchesMissingDataPostRequest;

  try {
    const data = await api.updateMatchesMissingDataApiUpdateMatchesMissingDataPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `1`] |

### Return type

**{ [key: string]: number | null; }**

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


## uploadReplayApiUploadReplayPost

> MatchInfo uploadReplayApiUploadReplayPost(file, xZuluBuild, macId, boardId, playerName, clientVersion, sourceTag)

Upload Replay

Upload a .rep file, save it to S3, parse it, and return the match info.  Optional source identifiers are stored on the ReplayFile row: - mac_id: gentool-style MAC-based identifier - board_id: stable identifier not tied to a network interface - player_name: in-game name the uploader played under - client_version: version string of the uploading client - source_tag: free-form uploader-supplied label  The optional X-Zulu-Build request header is captured on the ReplayFile; when it starts with \&quot;dev-\&quot; the replay and its match are flagged is_dev.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { UploadReplayApiUploadReplayPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // Blob
    file: BINARY_DATA_HERE,
    // string (optional)
    xZuluBuild: xZuluBuild_example,
    // string (optional)
    macId: macId_example,
    // string (optional)
    boardId: boardId_example,
    // string (optional)
    playerName: playerName_example,
    // string (optional)
    clientVersion: clientVersion_example,
    // string (optional)
    sourceTag: sourceTag_example,
  } satisfies UploadReplayApiUploadReplayPostRequest;

  try {
    const data = await api.uploadReplayApiUploadReplayPost(body);
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
| **file** | `Blob` |  | [Defaults to `undefined`] |
| **xZuluBuild** | `string` |  | [Optional] [Defaults to `undefined`] |
| **macId** | `string` |  | [Optional] [Defaults to `undefined`] |
| **boardId** | `string` |  | [Optional] [Defaults to `undefined`] |
| **playerName** | `string` |  | [Optional] [Defaults to `undefined`] |
| **clientVersion** | `string` |  | [Optional] [Defaults to `undefined`] |
| **sourceTag** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**MatchInfo**](MatchInfo.md)

### Authorization

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: `multipart/form-data`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

