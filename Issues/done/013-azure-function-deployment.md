## Parent Issue

`Issues/002-azure-infrastructure.md` — Infrastructure was planned but no deployment files exist.

## What to build

Deploy the Support Bot as an Azure Function App from the `feat/telegram-bot` branch to make the Telegram bot accessible via a public webhook URL.

### AFK (agent can do)

**1. Create deployment infrastructure:**
- Write `requirements.txt` with all Python dependencies
- Write `azure.yaml` for `azd` deployment
- Write Bicep template for: Function App (Python 3.13, Linux consumption), Storage Account, Application Insights
- The Function App must serve the FastAPI app via `function_app.py` (AsgiFunctionApp)

**2. Deploy:**
- Run `azd up` to provision infrastructure and deploy
- Or use `func azure functionapp publish` if Function App already exists

**3. Configure environment variables on the deployed Function App:**
All vars from `.env`:
- `GITHUB_PAT`
- `OPENAI_API_KEY`
- `OPENAI_ENDPOINT`
- `GROQ_API_KEY`
- `AZURE_STORAGE_CONNECTION_STRING`
- `TELEGRAM_BOT_TOKEN`
- `AZURE_FUNCTION_BASE_URL` (the deployed app's URL)
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `AZURE_STORAGE_CONTAINER` = `faiss-index`

**4. Verify:**
- `GET https://<app>.azurewebsites.net/api/search` returns 405 (not 404)
- `POST /api/telegram/webhook` returns 200 with a test payload
- Telegram webhook auto-registers on first startup

### HITL (user does)

- If Azure subscription has policy restrictions on resource creation
- Review and approve any Bicep template before deployment
- Test the Telegram bot manually after deployment

## Acceptance criteria

- [ ] `requirements.txt` exists with all deps
- [ ] `azure.yaml` + Bicep successfully provisions: Function App, Storage Account, App Insights
- [ ] `azd up` succeeds (or `func azure functionapp publish`)
- [ ] All 13 environment variables set on the Function App
- [ ] Telegram webhook auto-registers and bot responds to messages
- [ ] `/api/search` and `/api/save` endpoints accessible

## Blocked by

- None — all application features complete on `feat/telegram-bot`

## Not in scope

- CI/CD pipeline (GitHub Actions)
- Custom domain
- Staging slots
