# Deployment Runbook — Azure Functions (FlexConsumption)

End-to-end steps to deploy the Support Bot to Azure Functions. This is the procedure
that was actually used for the current production deployment (`azurefunctionapp100` in
`rg-azure_function`), including every gotcha hit along the way.

## Architecture summary

```
Telegram / Teams ─▶ Azure Function (FlexConsumption, Python 3.11)
                        │
                        ├─▶ FastAPI app (wrapped via AsgiMiddleware)
                        │       /api/search, /api/generate-doc,
                        │       /api/save, /api/messages,
                        │       /api/telegram/webhook
                        │
                        ├─▶ Azure Blob (FAISS index + index_map.json)
                        ├─▶ OpenAI / Groq APIs
                        └─▶ GitHub Contents API (commit docs)
```

The function package layout:

```
repo-root/
├── function_app.py              # entrypoint: catch-all route → AsgiMiddleware → FastAPI
├── host.json                    # runtime config
├── requirements.txt             # Python deps installed by Oryx
├── .funcignore                  # excludes from deployment package
└── blocker_doc_and_solution_bot/
    ├── __init__.py              # required, do not delete (PEP 420 is brittle here)
    ├── search_api/app.py        # FastAPI app, routes prefixed with /api/
    ├── doc_generator/           # Groq doc generation
    ├── github_commit/           # GitHub Contents API commit
    ├── index_builder/, index_updater/
    ├── teams_bot/, telegram_bot/
    └── conversation_state/, analytics/
```

## Prerequisites

- `az` (Azure CLI), `func` (Azure Functions Core Tools v4+)
- Logged in: `az login`
- Subscription set: `az account set --subscription <SUB_ID>`
- A **FlexConsumption** Function App exists. Do not use the old Linux Consumption (Y1)
  SKU for fresh deployments — see "Gotcha 1" below.
- A storage account containing the FAISS index (`faiss.index` and `index_map.json`
  in a container named `faiss-index`).

Current production resources:

| Resource | Name | Resource group |
|---|---|---|
| Function App | `azurefunctionapp100` | `rg-azure_function` |
| FAISS storage | `blockerbotblob` | `rg-azure_function` |
| Deployment storage (auto) | `rgazurefunctiona33b` | `rg-azure_function` |
| App Insights | `azurefunctionapp100` | `rg-azure_function` |

Base URL: `https://azurefunctionapp100-gfcrhhedakbrhzgx.eastus-01.azurewebsites.net`

## Step 1 — Configure app settings

All values must be set on the Function App. Use the Azure portal or `az`:

```bash
APP=azurefunctionapp100
RG=rg-azure_function

az functionapp config appsettings set -g $RG -n $APP --settings \
  OPENAI_API_KEY="<key>" \
  OPENAI_ENDPOINT="https://<resource>.openai.azure.com/openai/v1" \
  GROQ_API_KEY="<key>" \
  GITHUB_PAT="<github-personal-access-token>" \
  GITHUB_REPO_OWNER="abiolaks" \
  GITHUB_REPO_NAME="blocker_doc_and_solution_bot" \
  AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=blockerbotblob;AccountKey=<key>;EndpointSuffix=core.windows.net" \
  AZURE_STORAGE_CONTAINER="faiss-index" \
  TELEGRAM_BOT_TOKEN="<bot-token>" \
  AZURE_FUNCTION_BASE_URL="https://$APP-<suffix>.<region>.azurewebsites.net" \
  MICROSOFT_APP_ID="<bot-framework-app-id>"
```

Notes:

- `AZURE_FUNCTION_BASE_URL` must be the full external URL of the deployed app.
  The startup code uses it to auto-register the Telegram webhook.
- `MICROSOFT_APP_ID` is the AAD client ID the Teams bot identifies as. **No
  `MICROSOFT_APP_PASSWORD`** because the Teams bot uses a user-assigned managed
  identity (see Step 4).
- Do **not** wrap connection strings in extra double-quotes — Azure does not
  strip them and downstream parsing breaks.

## Step 2 — Deploy code

From the repo root:

```bash
func azure functionapp publish azurefunctionapp100 --python
```

What happens:

1. `func` zips the source (respecting `.funcignore`) and uploads to
   `rgazurefunctiona33b` → `app-package-azurefunctionapp100-<id>` container.
2. Kudu's Oryx build runs `pip install -r requirements.txt` on a Linux image
   matching the Function App's Python version, producing a release zip.
3. The release zip is mounted into the worker via the FlexConsumption deployment
   pipeline; `WEBSITE_RUN_FROM_PACKAGE` is updated automatically.
4. Sync-triggers runs, the host restarts, and discovered functions are listed.

A clean deploy prints:

```
Functions in azurefunctionapp100:
    http_app_func - [httpTrigger]
        Invoke url: https://<host>/api/{*route}
```

Local Python version warnings are safe — the build runs remotely.

## Step 3 — Verify

```bash
BASE=https://azurefunctionapp100-gfcrhhedakbrhzgx.eastus-01.azurewebsites.net

# Search (should return 200 with results)
curl -X POST -H 'Content-Type: application/json' \
  -d '{"query":"docker login error"}' $BASE/api/search

# Doc generation (should return 200 with markdown)
curl -X POST -H 'Content-Type: application/json' \
  -d '{"error":"x","solution":"y","project":"z"}' $BASE/api/generate-doc

# Telegram webhook auto-registered
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

Tail Function App logs (Application Insights):

```bash
az monitor app-insights query --app azurefunctionapp100 -g rg-azure_function \
  --analytics-query "traces | where timestamp > ago(5m) | order by timestamp desc | take 30 | project timestamp, severityLevel, message"
```

## Step 4 — Teams bot (user-assigned managed identity)

Setting `MICROSOFT_APP_ID` alone is not enough for the Teams `/api/messages`
endpoint. Additional setup needed:

1. Create (or reuse) a user-assigned managed identity in the same tenant as the
   Azure Bot resource.
2. Attach the identity to the Function App:
   ```bash
   az functionapp identity assign -g $RG -n $APP \
     --identities /subscriptions/<SUB>/resourceGroups/<RG>/providers/Microsoft.ManagedIdentity/userAssignedIdentities/<NAME>
   ```
3. In the Azure Bot resource (Bot Framework registration), set:
   - Microsoft App Type: `UserAssignedMSI`
   - App ID: the **client ID** of the managed identity (this is the value put in
     `MICROSOFT_APP_ID`)
   - App Tenant ID: your tenant
4. Add the bot's messaging endpoint:
   `https://<app>.azurewebsites.net/api/messages`

## Gotchas encountered

### 1. Don't use legacy Linux Consumption (Y1) for first-time deploys

A fresh Linux Consumption Function App returns **503 on both the front-door
and Kudu (SCM)** until a valid code package exists. This blocks
`func publish`, which needs Kudu to upload — chicken-and-egg. Symptoms:

```
Unable to connect to the Azure Function App.
Details: Response status code does not indicate success: 503 (Site Unavailable).
```

FlexConsumption deploys via the management plane (OneDeploy) instead, and
does not need Kudu to be reachable, so first-time deploys work cleanly.

### 2. `ModuleNotFoundError: No module named 'aiohttp'`

`botbuilder-core` declares `aiohttp` as a runtime dependency but pip in the
Oryx build environment can miss it. Pin it explicitly in `requirements.txt`:

```
aiohttp>=3.9,<4.0
```

### 3. `func.AsgiFunctionApp` produces invalid route template

```
An error occurred while creating the route with name 'http_app_func' and
template 'api//{*route}'. The route template separator character '/' cannot
appear consecutively.
```

`AsgiFunctionApp` registers its catch-all as `/{*route}` (leading slash);
the runtime prepends the route prefix `api/` producing `api//{*route}`.
Workaround — write the wrapper manually with no leading slash:

```python
import azure.functions as func
from blocker_doc_and_solution_bot.search_api.app import app as fastapi_app

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(
    route="{*route}",
    methods=[func.HttpMethod.GET, func.HttpMethod.POST, func.HttpMethod.PUT,
             func.HttpMethod.DELETE, func.HttpMethod.PATCH,
             func.HttpMethod.HEAD, func.HttpMethod.OPTIONS],
    auth_level=func.AuthLevel.ANONYMOUS,
)
async def http_app_func(req, context):
    return await func.AsgiMiddleware(fastapi_app).handle_async(req, context)
```

### 4. ASGI lifespan never fires through `AsgiMiddleware`

FastAPI's `lifespan` context manager is **not driven** by
`func.AsgiMiddleware` — each invocation handles a single request/response
without the ASGI lifespan startup/shutdown protocol. Any code in the
lifespan handler (loading FAISS, registering webhooks) never runs, and
endpoints fail with `Search index not loaded`.

Fix — initialise at module import time instead, so the worker process loads
state once when it boots:

```python
def _initialize_state() -> None:
    global _openai_client, _faiss_index, _index_map
    # ... read env, build clients, load FAISS ...

_initialize_state()  # runs at module import

app = FastAPI(title="Support Bot Search API")  # no lifespan=
```

### 5. FastAPI routes need the `/api/` prefix

`AsgiMiddleware` forwards the full request path to FastAPI without
stripping the runtime's `api/` prefix. Routes registered as `/search`
return FastAPI's `{"detail":"Not Found"}` for requests to `/api/search`.

Fix — register every route with the `/api/` prefix:

```python
@app.post("/api/search", response_model=SearchResponse)
def search(...): ...
```

### 6. Package directory needs an explicit `__init__.py`

`blocker_doc_and_solution_bot/` without an `__init__.py` works locally as a
PEP 420 namespace package, but several pieces of Functions tooling expect a
regular package. Add an empty `blocker_doc_and_solution_bot/__init__.py`.

## Files this deployment depends on

| File | Why it matters |
|---|---|
| `function_app.py` | Catch-all HTTP trigger wrapping the FastAPI app |
| `host.json` | Functions runtime version (`~4`) and extension bundle |
| `requirements.txt` | Deps installed by Oryx remote build |
| `.funcignore` | Keeps `.azure/`, `Knowledge_base/`, demo scripts, etc. out of the deploy zip |
| `blocker_doc_and_solution_bot/__init__.py` | Marks the directory as a regular package |
| `blocker_doc_and_solution_bot/search_api/app.py` | FastAPI app, eager init, `/api/` prefixed routes |

## Re-running the deployment

Day-2 deploys are simple:

```bash
func azure functionapp publish azurefunctionapp100 --python
```

No infra changes needed. Settings persist across deploys.

## Cleanup of the failed Y1 stack

The original Linux Consumption stack (`rg-prod`: `blockerbotprod-bot-func`,
`blockerbotprodblob`, `blockerbotprod-plan`, App Insights) was abandoned
after the chicken-and-egg 503 issue described above. It was deleted with:

```bash
az group delete -n rg-prod --yes --no-wait
```
