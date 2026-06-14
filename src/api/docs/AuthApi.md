# AuthApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**discordCallbackApiAuthDiscordCallbackGet**](AuthApi.md#discordcallbackapiauthdiscordcallbackget) | **GET** /api/auth/discord/callback | Discord Callback |
| [**discordLoginApiAuthDiscordLoginGet**](AuthApi.md#discordloginapiauthdiscordloginget) | **GET** /api/auth/discord/login | Discord Login |
| [**logoutApiAuthLogoutPost**](AuthApi.md#logoutapiauthlogoutpost) | **POST** /api/auth/logout | Logout |
| [**meApiAuthMeGet**](AuthApi.md#meapiauthmeget) | **GET** /api/auth/me | Me |
| [**selectPlayerApiAuthSelectPlayerPost**](AuthApi.md#selectplayerapiauthselectplayerpost) | **POST** /api/auth/select_player | Select Player |



## discordCallbackApiAuthDiscordCallbackGet

> any discordCallbackApiAuthDiscordCallbackGet(code, state)

Discord Callback

Handle Discord\&#39;s redirect: validate state, upsert the user, set session.

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { DiscordCallbackApiAuthDiscordCallbackGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // string (optional)
    code: code_example,
    // string (optional)
    state: state_example,
  } satisfies DiscordCallbackApiAuthDiscordCallbackGetRequest;

  try {
    const data = await api.discordCallbackApiAuthDiscordCallbackGet(body);
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
| **code** | `string` |  | [Optional] [Defaults to `undefined`] |
| **state** | `string` |  | [Optional] [Defaults to `undefined`] |

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


## discordLoginApiAuthDiscordLoginGet

> any discordLoginApiAuthDiscordLoginGet()

Discord Login

Kick off the OAuth flow: redirect the browser to Discord.

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { DiscordLoginApiAuthDiscordLoginGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  try {
    const data = await api.discordLoginApiAuthDiscordLoginGet();
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


## logoutApiAuthLogoutPost

> { [key: string]: boolean; } logoutApiAuthLogoutPost()

Logout

Clear the session cookie.

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { LogoutApiAuthLogoutPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  try {
    const data = await api.logoutApiAuthLogoutPost();
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

**{ [key: string]: boolean; }**

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


## meApiAuthMeGet

> AuthStatus meApiAuthMeGet()

Me

Return the current auth status (logged out, or the user + selectable names).

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { MeApiAuthMeGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  try {
    const data = await api.meApiAuthMeGet();
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

[**AuthStatus**](AuthStatus.md)

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


## selectPlayerApiAuthSelectPlayerPost

> AuthStatus selectPlayerApiAuthSelectPlayerPost(selectPlayerRequest)

Select Player

Claim an in-game name (first-login step). Name must be in PLAYER_NAMES.

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { SelectPlayerApiAuthSelectPlayerPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // SelectPlayerRequest
    selectPlayerRequest: ...,
  } satisfies SelectPlayerApiAuthSelectPlayerPostRequest;

  try {
    const data = await api.selectPlayerApiAuthSelectPlayerPost(body);
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
| **selectPlayerRequest** | [SelectPlayerRequest](SelectPlayerRequest.md) |  | |

### Return type

[**AuthStatus**](AuthStatus.md)

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

