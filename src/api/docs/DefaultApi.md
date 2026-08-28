# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**backfillGameNightSummariesApiBackfillGameNightSummariesPost**](DefaultApi.md#backfillgamenightsummariesapibackfillgamenightsummariespost) | **POST** /api/backfill_game_night_summaries | Backfill Game Night Summaries |
| [**backfillMatchCompositionApiBackfillCompositionPost**](DefaultApi.md#backfillmatchcompositionapibackfillcompositionpost) | **POST** /api/backfill/composition | Backfill Match Composition |
| [**backfillPlayerRolesApiBackfillPlayerRolesPost**](DefaultApi.md#backfillplayerrolesapibackfillplayerrolespost) | **POST** /api/backfill_player_roles/ | Backfill Player Roles |
| [**backfillTournamentGamesApiBackfillTournamentGamesPost**](DefaultApi.md#backfilltournamentgamesapibackfilltournamentgamespost) | **POST** /api/backfill/tournament_games | Backfill Tournament Games |
| [**balanceTeamsApiBalanceTeamsGet**](DefaultApi.md#balanceteamsapibalanceteamsget) | **GET** /api/balance_teams/ | Balance Teams |
| [**cleanupShortMatchesApiCleanupShortMatchesPost**](DefaultApi.md#cleanupshortmatchesapicleanupshortmatchespost) | **POST** /api/cleanup_short_matches/ | Cleanup Short Matches |
| [**clearDetailsCacheApiClearDetailsCachePost**](DefaultApi.md#cleardetailscacheapicleardetailscachepost) | **POST** /api/clear_details_cache/ | Clear Details Cache |
| [**computeMatchCompositionApiMatchesMatchIdCompositionPost**](DefaultApi.md#computematchcompositionapimatchesmatchidcompositionpost) | **POST** /api/matches/{match_id}/composition | Compute Match Composition |
| [**debugMatchApiDebugMatchMatchIdGet**](DefaultApi.md#debugmatchapidebugmatchmatchidget) | **GET** /api/debug/match/{match_id} | Debug Match |
| [**deleteOverrideApiOverrideMatchIdDelete**](DefaultApi.md#deleteoverrideapioverridematchiddelete) | **DELETE** /api/override/{match_id} | Delete Override |
| [**fixIncompleteApiFixIncompletePost**](DefaultApi.md#fixincompleteapifixincompletepost) | **POST** /api/fix_incomplete/ | Fix Incomplete |
| [**fixUnkPlayersApiFixUnkPlayerPost**](DefaultApi.md#fixunkplayersapifixunkplayerpost) | **POST** /api/fix_unk_player/ | Fix Unk Players |
| [**generateGameNightSummaryApiGenerateGameNightSummaryNightPost**](DefaultApi.md#generategamenightsummaryapigenerategamenightsummarynightpost) | **POST** /api/generate_game_night_summary/{night} | Generate Game Night Summary |
| [**generateTournamentReportApiGenerateTournamentReportTournamentNamePost**](DefaultApi.md#generatetournamentreportapigeneratetournamentreporttournamentnamepost) | **POST** /api/generate_tournament_report/{tournament_name} | Generate Tournament Report |
| [**getBuildOrdersApiBuildOrdersMatchIdGet**](DefaultApi.md#getbuildordersapibuildordersmatchidget) | **GET** /api/build_orders/{match_id} | Get Build Orders |
| [**getDatesApiDatesGet**](DefaultApi.md#getdatesapidatesget) | **GET** /api/dates/ | Get Dates |
| [**getDurationDistributionApiDurationDistributionGet**](DefaultApi.md#getdurationdistributionapidurationdistributionget) | **GET** /api/duration_distribution/ | Get Duration Distribution |
| [**getEligiblePlayersApiPlayerProfileEligiblePlayersGet**](DefaultApi.md#geteligibleplayersapiplayerprofileeligibleplayersget) | **GET** /api/player_profile/eligible_players | Get Eligible Players |
| [**getFfaStatsApiFfastatsGet**](DefaultApi.md#getffastatsapiffastatsget) | **GET** /api/ffastats | Get Ffa Stats |
| [**getFilesForMatchIdApiFilesForMatchGet**](DefaultApi.md#getfilesformatchidapifilesformatchget) | **GET** /api/files_for_match | Get Files For Match Id |
| [**getGeneralsStatsApiGeneralstatsGet**](DefaultApi.md#getgeneralsstatsapigeneralstatsget) | **GET** /api/generalstats | Get Generals Stats |
| [**getHeadToHeadApiPlayerRatingsHeadToHeadGet**](DefaultApi.md#getheadtoheadapiplayerratingsheadtoheadget) | **GET** /api/player_ratings/head_to_head/ | Get Head To Head |
| [**getMatchByIdApiMatchMatchIdGet**](DefaultApi.md#getmatchbyidapimatchmatchidget) | **GET** /api/match/{match_id} | Get Match By Id |
| [**getMatchDetailsApiDetailsMatchIdGet**](DefaultApi.md#getmatchdetailsapidetailsmatchidget) | **GET** /api/details/{match_id} | Get Match Details |
| [**getMatchJsonUrlApiDebugJsonUrlMatchIdGet**](DefaultApi.md#getmatchjsonurlapidebugjsonurlmatchidget) | **GET** /api/debug/json_url/{match_id} | Get Match Json Url |
| [**getMatchNarrativeApiNarrativeMatchIdGet**](DefaultApi.md#getmatchnarrativeapinarrativematchidget) | **GET** /api/narrative/{match_id} | Get Match Narrative |
| [**getMatchReplayUrlApiReplayUrlMatchIdGet**](DefaultApi.md#getmatchreplayurlapireplayurlmatchidget) | **GET** /api/replay_url/{match_id} | Get Match Replay Url |
| [**getMatchesByDateApiMatchesByDateDateGet**](DefaultApi.md#getmatchesbydateapimatchesbydatedateget) | **GET** /api/matches/by_date/{date} | Get Matches By Date |
| [**getOverridesApiOverridesGet**](DefaultApi.md#getoverridesapioverridesget) | **GET** /api/overrides | Get Overrides |
| [**getPlayerColorsApiPlayerColorsGet**](DefaultApi.md#getplayercolorsapiplayercolorsget) | **GET** /api/player_colors/ | Get Player Colors |
| [**getPlayerGameCountsApiPlayerGameCountsGet**](DefaultApi.md#getplayergamecountsapiplayergamecountsget) | **GET** /api/player_game_counts/ | Get Player Game Counts |
| [**getPlayerHeadToHeadApiPlayerHeadToHeadGet**](DefaultApi.md#getplayerheadtoheadapiplayerheadtoheadget) | **GET** /api/player_head_to_head/ | Get Player Head To Head |
| [**getPlayerProfileApiPlayerProfileGet**](DefaultApi.md#getplayerprofileapiplayerprofileget) | **GET** /api/player_profile/ | Get Player Profile |
| [**getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet**](DefaultApi.md#getplayerratingdailychangesapiplayerratingsdailychangesget) | **GET** /api/player_ratings/daily_changes/ | Get Player Rating Daily Changes |
| [**getPlayerRatingsApiPlayerRatingsGet**](DefaultApi.md#getplayerratingsapiplayerratingsget) | **GET** /api/player_ratings/ | Get Player Ratings |
| [**getPlayerSkillsApiPlayerSkillsGet**](DefaultApi.md#getplayerskillsapiplayerskillsget) | **GET** /api/player_skills/ | Get Player Skills |
| [**getPlayerStatsApiPlayerstatsGet**](DefaultApi.md#getplayerstatsapiplayerstatsget) | **GET** /api/playerstats | Get Player Stats |
| [**getPlayerSynergyApiPlayerRatingsSynergyGet**](DefaultApi.md#getplayersynergyapiplayerratingssynergyget) | **GET** /api/player_ratings/synergy/ | Get Player Synergy |
| [**getPlayerTeamGameCountsApiPlayerGameCountsTeamGet**](DefaultApi.md#getplayerteamgamecountsapiplayergamecountsteamget) | **GET** /api/player_game_counts/team/ | Get Player Team Game Counts |
| [**getPowerStatsApiPowerStatsGet**](DefaultApi.md#getpowerstatsapipowerstatsget) | **GET** /api/power_stats/ | Get Power Stats |
| [**getPresignedForMatchIdApiPresignedUrlsForMatchGet**](DefaultApi.md#getpresignedformatchidapipresignedurlsformatchget) | **GET** /api/presigned_urls_for_match | Get Presigned For Match Id |
| [**getRatingUpsetsApiPlayerRatingsUpsetsGet**](DefaultApi.md#getratingupsetsapiplayerratingsupsetsget) | **GET** /api/player_ratings/upsets/ | Get Rating Upsets |
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
| [**listTournamentsApiTournamentsGet**](DefaultApi.md#listtournamentsapitournamentsget) | **GET** /api/tournaments | List Tournaments |
| [**partitionTeamsApiPartitionTeamsTeamSizeGet**](DefaultApi.md#partitionteamsapipartitionteamsteamsizeget) | **GET** /api/partition_teams/{team_size} | Partition Teams |
| [**predictFactionMatchupApiPredictFactionMatchupGet**](DefaultApi.md#predictfactionmatchupapipredictfactionmatchupget) | **GET** /api/predict/faction_matchup | Predict Faction Matchup |
| [**predictFactionMatrixApiPredictFactionMatrixGet**](DefaultApi.md#predictfactionmatrixapipredictfactionmatrixget) | **GET** /api/predict/faction_matrix | Predict Faction Matrix |
| [**predictFromFeaturesApiPredictPost**](DefaultApi.md#predictfromfeaturesapipredictpost) | **POST** /api/predict | Predict From Features |
| [**predictMatchApiPredictMatchMatchIdGet**](DefaultApi.md#predictmatchapipredictmatchmatchidget) | **GET** /api/predict/match/{match_id} | Predict Match |
| [**predictOverTimeApiPredictOverTimeMatchIdGet**](DefaultApi.md#predictovertimeapipredictovertimematchidget) | **GET** /api/predict/over_time/{match_id} | Predict Over Time |
| [**randomizeDraftApiDraftRandomizePost**](DefaultApi.md#randomizedraftapidraftrandomizepost) | **POST** /api/draft/randomize | Randomize Draft |
| [**recomputePlayerProfilesApiPlayerProfileRecomputePost**](DefaultApi.md#recomputeplayerprofilesapiplayerprofilerecomputepost) | **POST** /api/player_profile/recompute | Recompute Player Profiles |
| [**recomputeSuperlativesApiSuperlativesRecomputePost**](DefaultApi.md#recomputesuperlativesapisuperlativesrecomputepost) | **POST** /api/superlatives/recompute | Recompute Superlatives |
| [**refreshMatchesFromJsonApiRefreshMatchesFromJsonPost**](DefaultApi.md#refreshmatchesfromjsonapirefreshmatchesfromjsonpost) | **POST** /api/refresh_matches_from_json/ | Refresh Matches From Json |
| [**registerMatchesApiRegisterMatchesPost**](DefaultApi.md#registermatchesapiregistermatchespost) | **POST** /api/register_matches/ | Register Matches |
| [**registerReplayUrlApiRegisterReplayUrlPost**](DefaultApi.md#registerreplayurlapiregisterreplayurlpost) | **POST** /api/register_replay_url | Register Replay Url |
| [**reparseApiReparseMatchIdPost**](DefaultApi.md#reparseapireparsematchidpost) | **POST** /api/reparse/{match_id} | Reparse |
| [**reparseBeforeDateApiReparseBeforeDatePost**](DefaultApi.md#reparsebeforedateapireparsebeforedatepost) | **POST** /api/reparse_before_date/ | Reparse Before Date |
| [**reparseNonV2ApiReparseNonV2Post**](DefaultApi.md#reparsenonv2apireparsenonv2post) | **POST** /api/reparse_non_v2/ | Reparse Non V2 |
| [**reparseRecentApiReparseRecentPost**](DefaultApi.md#reparserecentapireparserecentpost) | **POST** /api/reparse_recent/ | Reparse Recent |
| [**replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet**](DefaultApi.md#replayswithoutplayerstatsapireplayswithoutplayerstatsget) | **GET** /api/replays_without_playerstats/ | Replays Without Playerstats |
| [**resetMatchApiMatchMatchIdDelete**](DefaultApi.md#resetmatchapimatchmatchiddelete) | **DELETE** /api/match/{match_id} | Reset Match |
| [**scrapeApiScrapeDaysPost**](DefaultApi.md#scrapeapiscrapedayspost) | **POST** /api/scrape/{days} | Scrape |
| [**setOverrideApiSetOverridePost**](DefaultApi.md#setoverrideapisetoverridepost) | **POST** /api/set_override/ | Set Override |
| [**testTournamentReportApiTestTournamentReportTournamentNamePost**](DefaultApi.md#testtournamentreportapitesttournamentreporttournamentnamepost) | **POST** /api/test_tournament_report/{tournament_name} | Test Tournament Report |
| [**tournamentGamesForApiTournamentsSlugGamesGet**](DefaultApi.md#tournamentgamesforapitournamentssluggamesget) | **GET** /api/tournaments/{slug}/games | Tournament Games For |
| [**uploadReplayApiUploadReplayPost**](DefaultApi.md#uploadreplayapiuploadreplaypost) | **POST** /api/upload_replay | Upload Replay |



## backfillGameNightSummariesApiBackfillGameNightSummariesPost

> GameNightBackfill backfillGameNightSummariesApiBackfillGameNightSummariesPost(days, maxToUpdate)

Backfill Game Night Summaries

Fill in missing LLM recaps for the last &#x60;&#x60;days&#x60;&#x60; game nights.  **Every night this writes is a real, billed LLM call**, which is what shapes the two knobs. &#x60;&#x60;days&#x60;&#x60; says how far back to *look*; &#x60;&#x60;max_to_update&#x60;&#x60; says how many calls this run may *spend* (the backfill endpoint pattern - default 1, run it again to continue). Nights are taken newest first, so a small budget buys the recaps people are most likely to read.  Never overwrites: a night with a stored row is reported &#x60;&#x60;already_summarized&#x60;&#x60; and skipped, because the stored text is the delivery mechanism rather than a cache. Use &#x60;&#x60;POST /api/generate_game_night_summary/{night}?force&#x3D;true&#x60;&#x60; to rewrite one deliberately. Nights below the floor the nightly job uses (&#x60;&#x60;night_summary.MIN_MATCHES_FOR_SUMMARY&#x60;&#x60;) are skipped too, and the night currently in progress is never in the window - see &#x60;&#x60;queries.closed_nights_within&#x60;&#x60;.  The report lists every night considered, so a run with the default budget doubles as a dry run of the next one.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { BackfillGameNightSummariesApiBackfillGameNightSummariesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number (optional)
    days: 56,
    // number (optional)
    maxToUpdate: 56,
  } satisfies BackfillGameNightSummariesApiBackfillGameNightSummariesPostRequest;

  try {
    const data = await api.backfillGameNightSummariesApiBackfillGameNightSummariesPost(body);
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
| **days** | `number` |  | [Optional] [Defaults to `7`] |
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `1`] |

### Return type

[**GameNightBackfill**](GameNightBackfill.md)

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


## backfillMatchCompositionApiBackfillCompositionPost

> { [key: string]: number | null; } backfillMatchCompositionApiBackfillCompositionPost(maxToUpdate)

Backfill Match Composition

Backfill and persist the composition for matches missing it.

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

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies BackfillMatchCompositionApiBackfillCompositionPostRequest;

  try {
    const data = await api.backfillMatchCompositionApiBackfillCompositionPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `100`] |

### Return type

**{ [key: string]: number | null; }**

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


## backfillPlayerRolesApiBackfillPlayerRolesPost

> { [key: string]: number | null; } backfillPlayerRolesApiBackfillPlayerRolesPost(maxToUpdate, maxConcurrent)

Backfill Player Roles

Stamp match_players.role from each match\&#39;s already-parsed replay JSON.  Reads the stored S3 JSON - does NOT call cncstats - so this is free to run in bulk. Idempotent and incremental: it only looks at matches that still have a role-less player row, so it can be called repeatedly until &#x60;remaining&#x60; is 0.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { BackfillPlayerRolesApiBackfillPlayerRolesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number (optional)
    maxToUpdate: 56,
    // number (optional)
    maxConcurrent: 56,
  } satisfies BackfillPlayerRolesApiBackfillPlayerRolesPostRequest;

  try {
    const data = await api.backfillPlayerRolesApiBackfillPlayerRolesPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `100`] |
| **maxConcurrent** | `number` |  | [Optional] [Defaults to `16`] |

### Return type

**{ [key: string]: number | null; }**

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


## backfillTournamentGamesApiBackfillTournamentGamesPost

> { [key: string]: number | null; } backfillTournamentGamesApiBackfillTournamentGamesPost()

Backfill Tournament Games

Register the known tournaments and persist their game links.  Idempotent - re-running picks up games played since the last run and leaves admin-set (&#x60;&#x60;manual&#x60;&#x60;) links untouched, so this is safe to call repeatedly and is what the scrape job calls after registering matches. Unlike the other backfills there\&#39;s no &#x60;&#x60;max_to_update&#x60;&#x60;: detection is one in-memory pass over the already-cached match list, not per-match S3 work.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { BackfillTournamentGamesApiBackfillTournamentGamesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.backfillTournamentGamesApiBackfillTournamentGamesPost();
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

**{ [key: string]: number | null; }**

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

Win probability for every way of splitting &#x60;players&#x60; into two teams.  Held for six hours per roster: ask again with the same players and you get the same numbers back, even if games have landed in between. Change the roster and you get a fresh computation.

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


## cleanupShortMatchesApiCleanupShortMatchesPost

> { [key: string]: number | null; } cleanupShortMatchesApiCleanupShortMatchesPost(maxToUpdate)

Cleanup Short Matches

Delete match rows below the duration floor left by the old ingest order.  Before &#x60;matches.register_parsed_replay&#x60;, both ingest paths registered a match and only then asked whether the replay was long enough, so short games kept a committed row that no listing shows. Deleting them is only stable now that the floor is applied before the write. Run it repeatedly until &#x60;remaining&#x60; is 0.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { CleanupShortMatchesApiCleanupShortMatchesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies CleanupShortMatchesApiCleanupShortMatchesPostRequest;

  try {
    const data = await api.cleanupShortMatchesApiCleanupShortMatchesPost(body);
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

**{ [key: string]: number | null; }**

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


## clearDetailsCacheApiClearDetailsCachePost

> { [key: string]: number | null; } clearDetailsCacheApiClearDetailsCachePost()

Clear Details Cache

Drop every row of the durable MatchDetails cache and the in-process derivation fronting it. A debugging hatch - normal invalidation is per-match (reparse) or implicit via DETAILS_VERSION, and derivation changes should bump the version rather than lean on this.  Invalidating the corpus is a wider hammer than &#x60;details_from_id&#x60; alone, and deliberately so: reaching for a single cache by name is the vocabulary the registry exists to remove, and this also kicks the re-warm that emptying the durable tier makes worth doing.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ClearDetailsCacheApiClearDetailsCachePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.clearDetailsCacheApiClearDetailsCachePost();
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

**{ [key: string]: number | null; }**

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

**{ [key: string]: number | null; }**

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

**{ [key: string]: number | null; }**

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


## generateGameNightSummaryApiGenerateGameNightSummaryNightPost

> GameNightSummaryStatus generateGameNightSummaryApiGenerateGameNightSummaryNightPost(night, force)

Generate Game Night Summary

Write (or rewrite) one game night\&#39;s LLM recap by hand.  A real, billed LLM call - which is why this is the only way to reach the generator outside the nightly job, why it is ops-admin gated, and why it refuses by default when a row already exists. &#x60;&#x60;force&#x3D;true&#x60;&#x60; overwrites.  Unlike the nightly job this does not require the night to be closed, so it can be used to see what tonight would read like; the row it writes is then the one the page serves, so re-run it with &#x60;&#x60;force&#x60;&#x60; once the night ends.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GenerateGameNightSummaryApiGenerateGameNightSummaryNightPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // Date
    night: 2013-10-20,
    // boolean (optional)
    force: true,
  } satisfies GenerateGameNightSummaryApiGenerateGameNightSummaryNightPostRequest;

  try {
    const data = await api.generateGameNightSummaryApiGenerateGameNightSummaryNightPost(body);
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
| **force** | `boolean` |  | [Optional] [Defaults to `false`] |

### Return type

[**GameNightSummaryStatus**](GameNightSummaryStatus.md)

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

> { [key: string]: number; } getDatesApiDatesGet(player, mapName, gameFormat)

Get Dates

Every game night we have matches for, with how many were played.  The three optional filters narrow which matches are counted, so a filtered request returns only the nights that still have one and a count of what survived. They are the same three that &#x60;&#x60;/api/matches/by_date&#x60;&#x60; takes, on purpose: the Matches page sends its filter set to both, which is what keeps a night\&#39;s headline count equal to the number of matches it expands to.

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

  const body = {
    // string (optional)
    player: player_example,
    // string (optional)
    mapName: mapName_example,
    // string (optional)
    gameFormat: gameFormat_example,
  } satisfies GetDatesApiDatesGetRequest;

  try {
    const data = await api.getDatesApiDatesGet(body);
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
| **player** | `string` |  | [Optional] [Defaults to `undefined`] |
| **mapName** | `string` |  | [Optional] [Defaults to `undefined`] |
| **gameFormat** | `string` |  | [Optional] [Defaults to `undefined`] |

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


## getDurationDistributionApiDurationDistributionGet

> DurationDistribution getDurationDistributionApiDurationDistributionGet(bucketMinutes, maxMinutes, gameFormat)

Get Duration Distribution

How long our games run: a histogram plus per-format order statistics.  Computed over the competitive corpus, so it excludes comp-stomps and unfinished games - a disconnect at minute two is not a two-minute game, and a spike of them in the first bar would hide the real distribution. The &#x60;&#x60;game_format&#x60;&#x60; filter comes with the corpus dependency.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetDurationDistributionApiDurationDistributionGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number | Width of each histogram bar, in minutes (optional)
    bucketMinutes: 8.14,
    // number | Games at or beyond this land in the overflow bar (optional)
    maxMinutes: 8.14,
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetDurationDistributionApiDurationDistributionGetRequest;

  try {
    const data = await api.getDurationDistributionApiDurationDistributionGet(body);
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
| **bucketMinutes** | `number` | Width of each histogram bar, in minutes | [Optional] [Defaults to `2.0`] |
| **maxMinutes** | `number` | Games at or beyond this land in the overflow bar | [Optional] [Defaults to `60.0`] |
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**DurationDistribution**](DurationDistribution.md)

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


## getEligiblePlayersApiPlayerProfileEligiblePlayersGet

> Array&lt;string | null&gt; getEligiblePlayersApiPlayerProfileEligiblePlayersGet()

Get Eligible Players

Players with a full profile: enough games for favorites/badges to mean anything. Populates the profile page\&#39;s player picker.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetEligiblePlayersApiPlayerProfileEligiblePlayersGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getEligiblePlayersApiPlayerProfileEligiblePlayersGet();
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

[APIKeyHeader](../README.md#APIKeyHeader)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getFfaStatsApiFfastatsGet

> FFAStats getFfaStatsApiFfastatsGet()

Get Ffa Stats

Stats scoped to human free-for-all games (player wins, general win rates, ...).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetFfaStatsApiFfastatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getFfaStatsApiFfastatsGet();
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

[**FFAStats**](FFAStats.md)

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

Get generals stats.  Still takes a &#x60;ReplayManager&#x60; alongside the corpus: the value-destroyed totals are read from the &#x60;Statistic&#x60; rows the nightly superlatives recompute persists, which is a stored projection rather than something derived from the match list.

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
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
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
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

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

Get details about a particular match.  Result is cached in-process (see cache.details_from_id, invalidated on reparse/upload). Short browser hold only - a reparse or a WinnerOverride rewrites these details behind an unchanged URL. An unparsed match returns empty and is not cached, so it picks up data once processed.

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


## getMatchNarrativeApiNarrativeMatchIdGet

> MatchNarrative getMatchNarrativeApiNarrativeMatchIdGet(matchId)

Get Match Narrative

The match retold as an ordered list of beats.  A projection of the cached &#x60;&#x60;MatchDetails&#x60;&#x60; (see &#x60;&#x60;match_narrative&#x60;&#x60;), so it shares the durable, versioned details cache and runs no extra computation - the same arrangement as &#x60;&#x60;get_build_orders&#x60;&#x60; above. Entirely deterministic: no model call, identical on every request.  A match that isn\&#39;t in the corpus returns an empty narrative uncached; one whose replay hasn\&#39;t been parsed yet returns the headline with no beats, and picks up the rest once details exist.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMatchNarrativeApiNarrativeMatchIdGetRequest } from '';

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
  } satisfies GetMatchNarrativeApiNarrativeMatchIdGetRequest;

  try {
    const data = await api.getMatchNarrativeApiNarrativeMatchIdGet(body);
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

[**MatchNarrative**](MatchNarrative.md)

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

> ReplayDownload getMatchReplayUrlApiReplayUrlMatchIdGet(matchId)

Get Match Replay Url

Return a presigned S3 URL for the .rep file of a match, and its save name.

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

[**ReplayDownload**](ReplayDownload.md)

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

> Matches getMatchesByDateApiMatchesByDateDateGet(date, excludeDev, player, mapName, gameFormat)

Get Matches By Date

Get all matches for a specific date.  When exclude_dev is set, matches sourced from a \&quot;dev-\&quot; zulu build are omitted. The player/map/format filters match &#x60;&#x60;/api/dates&#x60;&#x60; - see the note there.

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
    // string (optional)
    player: player_example,
    // string (optional)
    mapName: mapName_example,
    // string (optional)
    gameFormat: gameFormat_example,
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
| **player** | `string` |  | [Optional] [Defaults to `undefined`] |
| **mapName** | `string` |  | [Optional] [Defaults to `undefined`] |
| **gameFormat** | `string` |  | [Optional] [Defaults to `undefined`] |

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


## getPlayerColorsApiPlayerColorsGet

> { [key: string]: string | null; } getPlayerColorsApiPlayerColorsGet()

Get Player Colors

Each player\&#39;s most common actual in-game color, keyed by player name - used as their primary identity color in the UI (see PlayerChip).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerColorsApiPlayerColorsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.getPlayerColorsApiPlayerColorsGet();
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


## getPlayerGameCountsApiPlayerGameCountsGet

> Array&lt;PlayerGameCount&gt; getPlayerGameCountsApiPlayerGameCountsGet()

Get Player Game Counts

Get all player names with their total game count, sorted by count descending.  Counts games *played*: spectating is not playing, and the sibling &#x60;&#x60;/api/player_team_game_counts/&#x60;&#x60; already counts competitors (via &#x60;&#x60;player_stats.get_player_stats&#x60;&#x60;), so reading every slot here made the two endpoints answer the same question differently.

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


## getPlayerHeadToHeadApiPlayerHeadToHeadGet

> HeadToHeadDetail getPlayerHeadToHeadApiPlayerHeadToHeadGet(player1, player2, gameFormat)

Get Player Head To Head

Detailed head-to-head record between two players (opposite-team games only).  Considers competitive games where both players took part on *different* teams; the winner of each game is the side whose team won. Aggregates the overall record, each player\&#39;s record by the general they piloted, and the record by map, plus the full game list (most recent first), and the value destroyed between them over their most recent shared games.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerHeadToHeadApiPlayerHeadToHeadGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string
    player1: player1_example,
    // string
    player2: player2_example,
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetPlayerHeadToHeadApiPlayerHeadToHeadGetRequest;

  try {
    const data = await api.getPlayerHeadToHeadApiPlayerHeadToHeadGet(body);
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
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**HeadToHeadDetail**](HeadToHeadDetail.md)

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


## getPlayerProfileApiPlayerProfileGet

> PlayerProfile getPlayerProfileApiPlayerProfileGet(player)

Get Player Profile

Full profile for one player.  &#x60;&#x60;computed&#x60;&#x60; is None until the batch recompute has run at the current PROFILE_VERSION (nightly, or via POST /api/player_profile/recompute).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerProfileApiPlayerProfileGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string
    player: player_example,
  } satisfies GetPlayerProfileApiPlayerProfileGetRequest;

  try {
    const data = await api.getPlayerProfileApiPlayerProfileGet(body);
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
| **player** | `string` |  | [Defaults to `undefined`] |

### Return type

[**PlayerProfile**](PlayerProfile.md)

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

> PlayerRatingData getPlayerRatingsApiPlayerRatingsGet(gameFormat, monthsBack)

Get Player Ratings

Ratings, rating history and recent form for every rated player.

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
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
    // number | Only use matches from the last N months (optional)
    monthsBack: 56,
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
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |
| **monthsBack** | `number` | Only use matches from the last N months | [Optional] [Defaults to `undefined`] |

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

Get player stats.  &#x60;game_format&#x60; stays a parameter here rather than coming from the corpus dependency: &#x60;player_stats.get_player_stats&#x60; filters per game *category* internally, which is finer-grained than &#x60;filter_by_format&#x60;.

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


## getPlayerSynergyApiPlayerRatingsSynergyGet

> Array&lt;PlayerSynergy&gt; getPlayerSynergyApiPlayerRatingsSynergyGet(minGamesTogether, regularization, mainRegularization, gameFormat)

Get Player Synergy

Pairwise synergy: do two players win more/less as teammates than their ratings predict.  Ridge logistic regression over team games with the rating model\&#39;s log-odds as a fixed offset, player main effects, and pairwise interaction terms. Sorted by synergy descending. See &#x60;&#x60;SYNERGY_METHODOLOGY.md&#x60;&#x60;.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPlayerSynergyApiPlayerRatingsSynergyGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number | Only return pairs that have played at least this many games together (optional)
    minGamesTogether: 56,
    // number | L2 shrinkage for pair synergy; higher = more conservative (optional)
    regularization: 8.14,
    // number | L2 shrinkage for per-player main effects; raise to stop strong players\' main effects running away and saturating pair synergy (optional)
    mainRegularization: 8.14,
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetPlayerSynergyApiPlayerRatingsSynergyGetRequest;

  try {
    const data = await api.getPlayerSynergyApiPlayerRatingsSynergyGet(body);
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
| **minGamesTogether** | `number` | Only return pairs that have played at least this many games together | [Optional] [Defaults to `3`] |
| **regularization** | `number` | L2 shrinkage for pair synergy; higher &#x3D; more conservative | [Optional] [Defaults to `10.0`] |
| **mainRegularization** | `number` | L2 shrinkage for per-player main effects; raise to stop strong players\&#39; main effects running away and saturating pair synergy | [Optional] [Defaults to `25.0`] |
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;PlayerSynergy&gt;**](PlayerSynergy.md)

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


## getPowerStatsApiPowerStatsGet

> PowerStats getPowerStatsApiPowerStatsGet(player)

Get Power Stats

One player\&#39;s generals-power habits, against the rest of the group.  Takes a &#x60;ReplayManager&#x60; rather than a corpus dependency: the whole answer comes from &#x60;queries.power_stats&#x60;, which folds the corpus once per corpus version and keeps only counters. Declaring &#x60;CompetitiveGames&#x60; here would build the match list on every request for a handler that never looks at it, and would key the fold by game format - four full passes over &#x60;match_details_cache&#x60; instead of one.  &#x60;player&#x60; is an &#x60;api_types.PlayerName&#x60;, so an in-game alias (\&quot;skp\&quot;) is resolved to the canonical name at validation, matching the names the projection stores.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetPowerStatsApiPowerStatsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string (optional)
    player: player_example,
  } satisfies GetPowerStatsApiPowerStatsGetRequest;

  try {
    const data = await api.getPowerStatsApiPowerStatsGet(body);
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
| **player** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**PowerStats**](PowerStats.md)

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


## getRatingUpsetsApiPlayerRatingsUpsetsGet

> Array&lt;RatingUpset&gt; getRatingUpsetsApiPlayerRatingsUpsetsGet(limit, withinDays, minSurprise, gameFormat)

Get Rating Upsets

Upsets: games where the model\&#39;s favored team lost.  Sorted by surprise (the favorite\&#39;s win-probability edge over the actual winner) descending. Optionally restricted to the last &#x60;&#x60;within_days&#x60;&#x60; days and to a &#x60;&#x60;min_surprise&#x60;&#x60; threshold; the top &#x60;&#x60;limit&#x60;&#x60; are returned.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetRatingUpsetsApiPlayerRatingsUpsetsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // number | Number of top upsets to return (optional)
    limit: 56,
    // number | Only include upsets from the last N days (optional)
    withinDays: 56,
    // number | Only include upsets with at least this surprise (0-1) (optional)
    minSurprise: 8.14,
    // string | Filter by game format: 1v1, 2v2, 3v3, 4v4 (optional)
    gameFormat: gameFormat_example,
  } satisfies GetRatingUpsetsApiPlayerRatingsUpsetsGetRequest;

  try {
    const data = await api.getRatingUpsetsApiPlayerRatingsUpsetsGet(body);
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
| **limit** | `number` | Number of top upsets to return | [Optional] [Defaults to `20`] |
| **withinDays** | `number` | Only include upsets from the last N days | [Optional] [Defaults to `undefined`] |
| **minSurprise** | `number` | Only include upsets with at least this surprise (0-1) | [Optional] [Defaults to `0.0`] |
| **gameFormat** | `string` | Filter by game format: 1v1, 2v2, 3v3, 4v4 | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;RatingUpset&gt;**](RatingUpset.md)

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

Get report for a specific tournament (round-robin only).

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

The slug of the tournament this match counted toward, or None.  Reads the persisted link rather than re-deriving membership, so an admin\&#39;s manual link (or exclusion) is reflected here too.

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


## listTournamentsApiTournamentsGet

> Array&lt;TournamentInfo&gt; listTournamentsApiTournamentsGet()

List Tournaments

Every tournament ever run, newest first, with its linked game count.  Counts come from an aggregate over the link table, so this page doesn\&#39;t depend on the match cache being warm.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { ListTournamentsApiTournamentsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.listTournamentsApiTournamentsGet();
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

[**Array&lt;TournamentInfo&gt;**](TournamentInfo.md)

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


## predictFactionMatchupApiPredictFactionMatchupGet

> FactionMatchupPrediction predictFactionMatchupApiPredictFactionMatchupGet(player1, player2, mapName)

Predict Faction Matchup

Rank every general-vs-general draw for a hypothetical 1v1 between player1 and player2, by running the win-prediction model once per (player1_general, player2_general) combination - 12x12 &#x3D; 144 calls.  Backs the \&quot;best possible draws\&quot; section of Bracket.tsx\&#39;s MatchupPopup, which calls this on every popup open - hence &#x60;&#x60;_faction_grid&#x60;&#x60; being a derivation; &#x60;&#x60;compute_ms&#x60;&#x60; is near-zero on a cache hit.  No map is known before the draw; omit map_name to use a placeholder the model treats as \&quot;unknown\&quot; (see &#x60;&#x60;_UNKNOWN_MAP_PLACEHOLDER&#x60;&#x60;), or pass a real map name to fix it.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PredictFactionMatchupApiPredictFactionMatchupGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string
    player1: player1_example,
    // string
    player2: player2_example,
    // string (optional)
    mapName: mapName_example,
  } satisfies PredictFactionMatchupApiPredictFactionMatchupGetRequest;

  try {
    const data = await api.predictFactionMatchupApiPredictFactionMatchupGet(body);
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
| **mapName** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**FactionMatchupPrediction**](FactionMatchupPrediction.md)

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


## predictFactionMatrixApiPredictFactionMatrixGet

> FactionMatrix predictFactionMatrixApiPredictFactionMatrixGet()

Predict Faction Matrix

The full 12x12 general-vs-general grid with both players and the map forced to the model\&#39;s UNK slot - a pure faction-vs-faction signal with no player identity or map mixed in. Same 144-call approach as faction_matchup, just with placeholder inputs instead of a real pair of players.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PredictFactionMatrixApiPredictFactionMatrixGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  try {
    const data = await api.predictFactionMatrixApiPredictFactionMatrixGet();
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

[**FactionMatrix**](FactionMatrix.md)

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


## predictFromFeaturesApiPredictPost

> MatchPrediction predictFromFeaturesApiPredictPost(predictRequest)

Predict From Features

Predict the winner from raw features: map, players, teams, generals.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PredictFromFeaturesApiPredictPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // PredictRequest
    predictRequest: ...,
  } satisfies PredictFromFeaturesApiPredictPostRequest;

  try {
    const data = await api.predictFromFeaturesApiPredictPost(body);
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
| **predictRequest** | [PredictRequest](PredictRequest.md) |  | |

### Return type

[**MatchPrediction**](MatchPrediction.md)

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


## predictMatchApiPredictMatchMatchIdGet

> MatchPrediction predictMatchApiPredictMatchMatchIdGet(matchId)

Predict Match

Predict the winner of an existing match by id.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PredictMatchApiPredictMatchMatchIdGetRequest } from '';

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
  } satisfies PredictMatchApiPredictMatchMatchIdGetRequest;

  try {
    const data = await api.predictMatchApiPredictMatchMatchIdGet(body);
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

[**MatchPrediction**](MatchPrediction.md)

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


## predictOverTimeApiPredictOverTimeMatchIdGet

> WinProbOverTime predictOverTimeApiPredictOverTimeMatchIdGet(matchId)

Predict Over Time

Win-probability-over-time curve for an existing match.  Streams the match\&#39;s parsed replay JSON from S3 and runs the sequence ONNX model, returning P(team A wins) at each 30-second window.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PredictOverTimeApiPredictOverTimeMatchIdGetRequest } from '';

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
  } satisfies PredictOverTimeApiPredictOverTimeMatchIdGetRequest;

  try {
    const data = await api.predictOverTimeApiPredictOverTimeMatchIdGet(body);
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

[**WinProbOverTime**](WinProbOverTime.md)

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


## recomputePlayerProfilesApiPlayerProfileRecomputePost

> { [key: string]: string | null; } recomputePlayerProfilesApiPlayerProfileRecomputePost()

Recompute Player Profiles

Trigger a profile batch recompute in the background and return immediately.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { RecomputePlayerProfilesApiPlayerProfileRecomputePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.recomputePlayerProfilesApiPlayerProfileRecomputePost();
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

> { [key: string]: number | null; } refreshMatchesFromJsonApiRefreshMatchesFromJsonPost(maxToUpdate)

Refresh Matches From Json

Re-parse existing JSON files from S3 and update DB matches if they differ.  Does NOT re-run cncstats - only reloads the already-parsed JSON from S3. Phase 1 (S3 fetches) runs in parallel; Phase 2 (DB writes) runs serially. Fetches up to max_to_update * 4 candidates to account for non-differing matches.

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

**{ [key: string]: number | null; }**

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

> { [key: string]: number | null; } registerMatchesApiRegisterMatchesPost(maxToUpdate)

Register Matches

Register Match rows for any ParsedReplayJson that has no corresponding Match.  &#x60;checked&#x60; counts replays read from S3, including ones declined as too short - so &#x60;updated: 0&#x60; with a non-zero &#x60;checked&#x60; means \&quot;run me again\&quot;, not \&quot;queue drained\&quot;.

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

  const body = {
    // number (optional)
    maxToUpdate: 56,
  } satisfies RegisterMatchesApiRegisterMatchesPostRequest;

  try {
    const data = await api.registerMatchesApiRegisterMatchesPost(body);
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
| **maxToUpdate** | `number` |  | [Optional] [Defaults to `100`] |

### Return type

**{ [key: string]: number | null; }**

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

Rerun the replay parser on this match.  On the cookie-session router, not the API-key one: the DebugData page\&#39;s reparse button drives this, and the key the browser ships is normal-tier by design. Authorization is the logged-in user being an admin.

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

> { [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; } reparseBeforeDateApiReparseBeforeDatePost(before, maxToUpdate)

Reparse Before Date

Re-run cncstats on matches whose parsed JSON was last updated before &#x60;before&#x60;.  Calls cncstats for each match - slower than refresh_matches_from_json but picks up new fields added to the parser output.

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

[**{ [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; }**](ResponseReparseBeforeDateApiReparseBeforeDatePostValue.md)

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

> { [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; } reparseNonV2ApiReparseNonV2Post(maxToUpdate, maxConcurrent)

Reparse Non V2

Re-run cncstats on matches whose parsed JSON was last updated before &#x60;before&#x60;.  Calls cncstats for each match - slower than refresh_matches_from_json but picks up new fields added to the parser output.

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

[**{ [key: string]: ResponseReparseBeforeDateApiReparseBeforeDatePostValue; }**](ResponseReparseBeforeDateApiReparseBeforeDatePostValue.md)

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

> Array&lt;ReplayWithoutPlayerStats&gt; replaysWithoutPlayerstatsApiReplaysWithoutPlayerstatsGet(maxToReturn)

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

[**Array&lt;ReplayWithoutPlayerStats&gt;**](ReplayWithoutPlayerStats.md)

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

**{ [key: string]: number | null; }**

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


## tournamentGamesForApiTournamentsSlugGamesGet

> Matches tournamentGamesForApiTournamentsSlugGamesGet(slug)

Tournament Games For

The matches linked to one tournament, newest first.  Driven off the persisted links, so this answers \&quot;every game of this tournament\&quot; for a finished bracket whose live state has since been reset. Links whose match is missing from the listing are skipped - the link table has no FK to matches on purpose (see db.TournamentGame).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { TournamentGamesForApiTournamentsSlugGamesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure API key authorization: APIKeyHeader
    apiKey: "YOUR API KEY",
  });
  const api = new DefaultApi(config);

  const body = {
    // string
    slug: slug_example,
  } satisfies TournamentGamesForApiTournamentsSlugGamesGetRequest;

  try {
    const data = await api.tournamentGamesForApiTournamentsSlugGamesGet(body);
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
| **slug** | `string` |  | [Defaults to `undefined`] |

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
    // string
    file: file_example,
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
| **file** | `string` |  | [Defaults to `undefined`] |
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

