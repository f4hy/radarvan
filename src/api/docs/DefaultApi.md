# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**backfillMatchCompositionApiBackfillCompositionPost**](DefaultApi.md#backfillmatchcompositionapibackfillcompositionpost) | **POST** /api/backfill/composition | Backfill Match Composition |
| [**balanceTeamsApiBalanceTeamsGet**](DefaultApi.md#balanceteamsapibalanceteamsget) | **GET** /api/balance_teams/ | Balance Teams |
| [**computeMatchCompositionApiMatchesMatchIdCompositionPost**](DefaultApi.md#computematchcompositionapimatchesmatchidcompositionpost) | **POST** /api/matches/{match_id}/composition | Compute Match Composition |
| [**debugMatchApiDebugMatchMatchIdGet**](DefaultApi.md#debugmatchapidebugmatchmatchidget) | **GET** /api/debug/match/{match_id} | Debug Match |
| [**deleteOverrideApiOverrideMatchIdDelete**](DefaultApi.md#deleteoverrideapioverridematchiddelete) | **DELETE** /api/override/{match_id} | Delete Override |
| [**fixIncompleteApiFixIncompletePost**](DefaultApi.md#fixincompleteapifixincompletepost) | **POST** /api/fix_incomplete/ | Fix Incomplete |
| [**fixUnkPlayersApiFixUnkPlayerPost**](DefaultApi.md#fixunkplayersapifixunkplayerpost) | **POST** /api/fix_unk_player/ | Fix Unk Players |
| [**generateTournamentReportApiGenerateTournamentReportTournamentNamePost**](DefaultApi.md#generatetournamentreportapigeneratetournamentreporttournamentnamepost) | **POST** /api/generate_tournament_report/{tournament_name} | Generate Tournament Report |
| [**getDatesApiDatesGet**](DefaultApi.md#getdatesapidatesget) | **GET** /api/dates/ | Get Dates |
| [**getFilesForMatchIdApiFilesForMatchGet**](DefaultApi.md#getfilesformatchidapifilesformatchget) | **GET** /api/files_for_match | Get Files For Match Id |
| [**getGeneralsStatsApiGeneralstatsGet**](DefaultApi.md#getgeneralsstatsapigeneralstatsget) | **GET** /api/generalstats | Get Generals Stats |
| [**getHeadToHeadApiPlayerRatingsHeadToHeadGet**](DefaultApi.md#getheadtoheadapiplayerratingsheadtoheadget) | **GET** /api/player_ratings/head_to_head/ | Get Head To Head |
| [**getMapDataApiMapDataMapNameGet**](DefaultApi.md#getmapdataapimapdatamapnameget) | **GET** /api/map_data/{map_name} | Get Map Data |
| [**getMapStatsApiMapStatsGet**](DefaultApi.md#getmapstatsapimapstatsget) | **GET** /api/map_stats/ | Get Map Stats |
| [**getMapsByPlayerCountApiMapsByPlayerCountGet**](DefaultApi.md#getmapsbyplayercountapimapsbyplayercountget) | **GET** /api/maps_by_player_count | Get Maps By Player Count |
| [**getMatchByIdApiMatchMatchIdGet**](DefaultApi.md#getmatchbyidapimatchmatchidget) | **GET** /api/match/{match_id} | Get Match By Id |
| [**getMatchDetailsApiDetailsMatchIdGet**](DefaultApi.md#getmatchdetailsapidetailsmatchidget) | **GET** /api/details/{match_id} | Get Match Details |
| [**getMatchJsonUrlApiDebugJsonUrlMatchIdGet**](DefaultApi.md#getmatchjsonurlapidebugjsonurlmatchidget) | **GET** /api/debug/json_url/{match_id} | Get Match Json Url |
| [**getMatchesApiMatchesMatchCountGet**](DefaultApi.md#getmatchesapimatchesmatchcountget) | **GET** /api/matches/{match_count} | Get Matches |
| [**getMatchesByDateApiMatchesByDateDateGet**](DefaultApi.md#getmatchesbydateapimatchesbydatedateget) | **GET** /api/matches/by_date/{date} | Get Matches By Date |
| [**getOverridesApiOverridesGet**](DefaultApi.md#getoverridesapioverridesget) | **GET** /api/overrides | Get Overrides |
| [**getPlayerGameCountsApiPlayerGameCountsGet**](DefaultApi.md#getplayergamecountsapiplayergamecountsget) | **GET** /api/player_game_counts/ | Get Player Game Counts |
| [**getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet**](DefaultApi.md#getplayerratingdailychangesapiplayerratingsdailychangesget) | **GET** /api/player_ratings/daily_changes/ | Get Player Rating Daily Changes |
| [**getPlayerRatingsApiPlayerRatingsGet**](DefaultApi.md#getplayerratingsapiplayerratingsget) | **GET** /api/player_ratings/ | Get Player Ratings |
| [**getPlayerSkillsApiPlayerSkillsGet**](DefaultApi.md#getplayerskillsapiplayerskillsget) | **GET** /api/player_skills/ | Get Player Skills |
| [**getPlayerStatsApiPlayerstatsGet**](DefaultApi.md#getplayerstatsapiplayerstatsget) | **GET** /api/playerstats | Get Player Stats |
| [**getPlayerTeamGameCountsApiPlayerGameCountsTeamGet**](DefaultApi.md#getplayerteamgamecountsapiplayergamecountsteamget) | **GET** /api/player_game_counts/team/ | Get Player Team Game Counts |
| [**getReplayByUrlApiReplayGet**](DefaultApi.md#getreplaybyurlapireplayget) | **GET** /api/replay | Get Replay By Url |
| [**getSuperlativesApiSuperlativesGet**](DefaultApi.md#getsuperlativesapisuperlativesget) | **GET** /api/superlatives | Get Superlatives |
| [**getTeamGamesWithoutWinnerApiTeamGamesWithoutWinnerGet**](DefaultApi.md#getteamgameswithoutwinnerapiteamgameswithoutwinnerget) | **GET** /api/team_games_without_winner/ | Get Team Games Without Winner |
| [**getTeamStatsApiTeamStatsGet**](DefaultApi.md#getteamstatsapiteamstatsget) | **GET** /api/team_stats/ | Get Team Stats |
| [**getTournamentReportApiTournamentReportTournamentNameGet**](DefaultApi.md#gettournamentreportapitournamentreporttournamentnameget) | **GET** /api/tournament_report/{tournament_name} | Get Tournament Report |
| [**getTournamentResultsApiTournamentResultsGet**](DefaultApi.md#gettournamentresultsapitournamentresultsget) | **GET** /api/tournament_results/ | Get Tournament Results |
| [**isTournamentGameApiIsTournamentGameMatchIdGet**](DefaultApi.md#istournamentgameapiistournamentgamematchidget) | **GET** /api/is_tournament_game/{match_id} | Is Tournament Game |
| [**listFilesApiFilesGet**](DefaultApi.md#listfilesapifilesget) | **GET** /api/files/ | List Files |
| [**listPendingUnprocessedApiFilesPendingUnprocessedGet**](DefaultApi.md#listpendingunprocessedapifilespendingunprocessedget) | **GET** /api/files/pending_unprocessed | List Pending Unprocessed |
| [**listReplaysApiReplaysGet**](DefaultApi.md#listreplaysapireplaysget) | **GET** /api/replays/ | List Replays |
| [**partitionTeamsApiPartitionTeamsTeamSizeGet**](DefaultApi.md#partitionteamsapipartitionteamsteamsizeget) | **GET** /api/partition_teams/{team_size} | Partition Teams |
| [**randomizeDraftApiDraftRandomizePost**](DefaultApi.md#randomizedraftapidraftrandomizepost) | **POST** /api/draft/randomize | Randomize Draft |
| [**recomputeSuperlativesApiSuperlativesRecomputePost**](DefaultApi.md#recomputesuperlativesapisuperlativesrecomputepost) | **POST** /api/superlatives/recompute | Recompute Superlatives |
| [**refreshMatchesFromJsonApiRefreshMatchesFromJsonPost**](DefaultApi.md#refreshmatchesfromjsonapirefreshmatchesfromjsonpost) | **POST** /api/refresh_matches_from_json/ | Refresh Matches From Json |
| [**registerMatchesApiRegisterMatchesPost**](DefaultApi.md#registermatchesapiregistermatchespost) | **POST** /api/register_matches/ | Register Matches |
| [**registerReplayUrlApiRegisterReplayUrlPost**](DefaultApi.md#registerreplayurlapiregisterreplayurlpost) | **POST** /api/register_replay_url | Register Replay Url |
| [**reparseApiReparseMatchIdPost**](DefaultApi.md#reparseapireparsematchidpost) | **POST** /api/reparse/{match_id} | Reparse |
| [**reparseBeforeDateApiReparseBeforeDatePost**](DefaultApi.md#reparsebeforedateapireparsebeforedatepost) | **POST** /api/reparse_before_date/ | Reparse Before Date |
| [**reparseNonV2ApiReparseNonV2Post**](DefaultApi.md#reparsenonv2apireparsenonv2post) | **POST** /api/reparse_non_v2/ | Reparse Non V2 |
| [**reparseRecentApiReparseRecentPost**](DefaultApi.md#reparserecentapireparserecentpost) | **POST** /api/reparse_recent/ | Reparse Recent |
| [**replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet**](DefaultApi.md#replayswithoutplayerstatsapireplayswithoutplayerstatsget) | **GET** /api/replays_without_playerstats/ | Replays Without Playerstats |
| [**repraseApiRepraseMatchIdPost**](DefaultApi.md#repraseapireprasematchidpost) | **POST** /api/reprase/{match_id} | Reprase |
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
  const api = new DefaultApi();

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

No authorization required

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

**{ [key: string]: number; }**

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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


## fixIncompleteApiFixIncompletePost

> { [key: string]: number; } fixIncompleteApiFixIncompletePost(maxToUpdate)

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
  const api = new DefaultApi();

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

**{ [key: string]: number; }**

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


## fixUnkPlayersApiFixUnkPlayerPost

> { [key: string]: number; } fixUnkPlayersApiFixUnkPlayerPost(maxToUpdate)

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
  const api = new DefaultApi();

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

**{ [key: string]: number; }**

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

**{ [key: string]: number; }**

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

[**{ [key: string]: ResponseGetFilesForMatchIdApiFilesForMatchGetValue; }**](ResponseGetFilesForMatchIdApiFilesForMatchGetValue.md)

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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


## getMatchesByDateApiMatchesByDateDateGet

> Matches getMatchesByDateApiMatchesByDateDateGet(date)

Get Matches By Date

Get all matches for a specific date.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchesByDateApiMatchesByDateDateGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // Date
    date: 2013-10-20,
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
  const api = new DefaultApi();

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

No authorization required

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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

No authorization required

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
  const api = new DefaultApi();

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

No authorization required

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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

[**Array&lt;ReplayFileSchema&gt;**](ReplayFileSchema.md)

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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


## partitionTeamsApiPartitionTeamsTeamSizeGet

> Array&lt;Array&lt;string&gt;&gt; partitionTeamsApiPartitionTeamsTeamSizeGet(teamSize, players)

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
  const api = new DefaultApi();

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

**Array<Array<string>>**

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
  const api = new DefaultApi();

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
  const api = new DefaultApi();

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

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## refreshMatchesFromJsonApiRefreshMatchesFromJsonPost

> { [key: string]: number; } refreshMatchesFromJsonApiRefreshMatchesFromJsonPost(maxToUpdate)

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
  const api = new DefaultApi();

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

**{ [key: string]: number; }**

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
  const api = new DefaultApi();

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


## reparseBeforeDateApiReparseBeforeDatePost

> { [key: string]: ResponseReparseRecentApiReparseRecentPostValue; } reparseBeforeDateApiReparseBeforeDatePost(before, maxToUpdate)

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
  const api = new DefaultApi();

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

[**{ [key: string]: ResponseReparseRecentApiReparseRecentPostValue; }**](ResponseReparseRecentApiReparseRecentPostValue.md)

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


## reparseNonV2ApiReparseNonV2Post

> { [key: string]: ResponseReparseRecentApiReparseRecentPostValue; } reparseNonV2ApiReparseNonV2Post(maxToUpdate, maxConcurrent)

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
  const api = new DefaultApi();

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

[**{ [key: string]: ResponseReparseRecentApiReparseRecentPostValue; }**](ResponseReparseRecentApiReparseRecentPostValue.md)

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
  const api = new DefaultApi();

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

**Array<{ [key: string]: any; }>**

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

> MatchInfo repraseApiRepraseMatchIdPost(matchId)

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


## resetMatchApiMatchMatchIdDelete

> { [key: string]: number; } resetMatchApiMatchMatchIdDelete(matchId)

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
  const api = new DefaultApi();

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

**{ [key: string]: number; }**

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
  const api = new DefaultApi();

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

**{ [key: string]: string | null; }**

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
  const api = new DefaultApi();

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


## updateMatchesMissingDataApiUpdateMatchesMissingDataPost

> { [key: string]: number; } updateMatchesMissingDataApiUpdateMatchesMissingDataPost(maxToUpdate)

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
  const api = new DefaultApi();

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

**{ [key: string]: number; }**

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


## uploadReplayApiUploadReplayPost

> MatchInfo uploadReplayApiUploadReplayPost(file)

Upload Replay

Upload a .rep file, save it to S3, parse it, and return the match info.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { UploadReplayApiUploadReplayPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // Blob
    file: BINARY_DATA_HERE,
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

### Return type

[**MatchInfo**](MatchInfo.md)

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

