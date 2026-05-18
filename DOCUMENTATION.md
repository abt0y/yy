# Gemini Web API (GWA) Documentation

This guide explains how to run GWA, export the Gemini Web authentication cookies, configure API tokens, and connect OpenAI-compatible, Claude-compatible, Gemini-native, OpenWebUI, and curl clients.

## 1. What GWA provides

GWA is a FastAPI proxy that translates common LLM API requests into Gemini Web requests through `gemini_webapi`.

| Surface | Base URL | Main endpoint |
| --- | --- | --- |
| OpenAI-compatible | `http://127.0.0.1:8000/v1` | `POST /v1/chat/completions` |
| Claude-compatible | `http://127.0.0.1:8000` | `POST /v1/messages` or `POST /anthropic/v1/messages` |
| Gemini-native | `http://127.0.0.1:8000` | `POST /gemini/generate` |
| Admin API | `http://127.0.0.1:8000` | `/admin/accounts`, `/admin/cookies`, `/admin/reload` |
| Admin UI | `http://127.0.0.1:8000/admin-ui` | Browser helper for cookie management |
| Health | `http://127.0.0.1:8000` | `GET /health` |

If you deploy the service, replace `http://127.0.0.1:8000` with your public HTTPS URL.

## 2. Install and start locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Validate startup:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

Expected `/health` before cookies are configured:

```json
{"status":"ok","accounts":0,"enabled_accounts":0}
```

## 3. Docker start

```bash
cp config.yaml.example config.yaml
docker compose up --build
```

Docker exposes the same local base URLs:

- OpenAI base URL: `http://127.0.0.1:8000/v1`
- Claude/Gemini/Admin base URL: `http://127.0.0.1:8000`

The compose file mounts these persistent folders:

- `./cookies` → `/app/cookies`
- `./uploads` → `/app/uploads`
- `./gemini_cookies` → `/app/gemini_cookies`

## 4. Export Gemini Web cookies/tokens

Gemini Web authentication uses Google session cookies. Treat these values like passwords. Use a dedicated Google/Gemini account when possible, do not commit them, and rotate them if exposed.

Required cookie:

- `__Secure-1PSID`

Usually recommended cookie:

- `__Secure-1PSIDTS`

### Option A: Export from Chrome DevTools Application tab

1. Open Chrome and go to `https://gemini.google.com/app`.
2. Log in with the Google account you want GWA to use.
3. Press `F12` or right-click the page and choose **Inspect**.
4. Open the **Application** tab.
5. In the left sidebar, expand **Storage** → **Cookies**.
6. Select `https://gemini.google.com`.
7. Search for `__Secure-1PSID`.
8. Copy the full value from the **Value** column.
9. Search for `__Secure-1PSIDTS` and copy the full value if present.
10. Paste the values into `config.yaml`, a `cookies/*.json` file, or the admin UI.

### Option B: Export from Chrome DevTools Network tab

1. Open `https://gemini.google.com/app` and make sure you are logged in.
2. Press `F12` or right-click and choose **Inspect**.
3. Open the **Network** tab.
4. Refresh the page.
5. Click a request to `gemini.google.com`.
6. Open **Headers**.
7. Find the **Request Headers** section.
8. Copy the `Cookie` header.
9. Extract these key-value pairs from the header:
   - `__Secure-1PSID=...`
   - `__Secure-1PSIDTS=...` if present
10. Keep only the cookie values, not the cookie names or semicolons.

### Option C: Add cookies through the admin UI

1. Start the server.
2. Open `http://127.0.0.1:8000/admin-ui`.
3. Paste `__Secure-1PSID` into the `__Secure-1PSID` field.
4. Paste `__Secure-1PSIDTS` into the optional field if present.
5. Click **Add**.
6. Confirm `/admin/accounts` shows one enabled account.

## 5. Configure Gemini cookies

### `config.yaml`

```yaml
gemini:
  cookies:
    - id: personal
      secure_1psid: "PASTE_SECURE_1PSID_HERE"
      secure_1psidts: "PASTE_SECURE_1PSIDTS_HERE"
      enabled: true
```

Restart the server after editing `config.yaml`.

### Cookie JSON file

Create `cookies/personal.json`:

```json
{
  "id": "personal",
  "secure_1psid": "PASTE_SECURE_1PSID_HERE",
  "secure_1psidts": "PASTE_SECURE_1PSIDTS_HERE",
  "enabled": true
}
```

Then either restart the server or reload cookie files:

```bash
curl -X POST http://127.0.0.1:8000/admin/reload
```

### Admin API

```bash
curl -X POST http://127.0.0.1:8000/admin/cookies \
  -H 'content-type: application/json' \
  -d '{
    "id": "personal",
    "secure_1psid": "PASTE_SECURE_1PSID_HERE",
    "secure_1psidts": "PASTE_SECURE_1PSIDTS_HERE",
    "enabled": true
  }'
```

List accounts:

```bash
curl http://127.0.0.1:8000/admin/accounts
```

Remove an account:

```bash
curl -X DELETE http://127.0.0.1:8000/admin/cookies/personal
```

## 6. Configure a proxy API token

GWA can protect all non-health endpoints with one or more bearer tokens. This is separate from Gemini cookies.

### Local shell export

```bash
export GWA_API_KEYS="my-local-token"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Call protected endpoints with:

```bash
curl http://127.0.0.1:8000/v1/models \
  -H 'Authorization: Bearer my-local-token'
```

### Multiple API tokens

```bash
export GWA_API_KEYS="token-one,token-two,token-three"
```

### `config.yaml`

```yaml
security:
  api_keys:
    - "token-one"
    - "token-two"
```

### Docker Compose

Add this under `services.gwa.environment`:

```yaml
GWA_API_KEYS: "my-production-token"
```

Then call the API with `Authorization: Bearer my-production-token`.

## 7. API base URL exports for clients

### OpenAI-compatible clients

```bash
export OPENAI_API_KEY="my-local-token"
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
```

If `GWA_API_KEYS` is empty, the `OPENAI_API_KEY` value can be any non-empty placeholder for SDKs that require it.

Python:

```python
from openai import OpenAI

client = OpenAI(
    api_key="my-local-token",
    base_url="http://127.0.0.1:8000/v1",
)

response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Say hello"}],
)
print(response.choices[0].message.content)
```

Streaming:

```python
for chunk in client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Stream one paragraph"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="")
```

curl:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'Authorization: Bearer my-local-token' \
  -H 'content-type: application/json' \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Hello from OpenAI format"}]
  }'
```

### Claude-compatible clients

```bash
export ANTHROPIC_API_KEY="my-local-token"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8000"
```

curl:

```bash
curl http://127.0.0.1:8000/v1/messages \
  -H 'Authorization: Bearer my-local-token' \
  -H 'content-type: application/json' \
  -d '{
    "model": "gemini-2.5-pro",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello from Claude format"}]
  }'
```

### Gemini-native clients

```bash
export GWA_BASE_URL="http://127.0.0.1:8000"
export GWA_API_KEY="my-local-token"
```

curl:

```bash
curl http://127.0.0.1:8000/gemini/generate \
  -H 'Authorization: Bearer my-local-token' \
  -H 'content-type: application/json' \
  -d '{
    "model": "gemini-2.5-pro",
    "prompt": "Hello from native GWA format"
  }'
```

## 8. OpenWebUI setup

1. Open OpenWebUI settings.
2. Add an OpenAI-compatible connection.
3. Set API Base URL to `http://127.0.0.1:8000/v1` for local use, or your deployed `https://.../v1` URL.
4. Set API Key to your `GWA_API_KEYS` token. If auth is disabled, use any placeholder value.
5. Use a model ID from `/v1/models`, for example `gemini-2.5-pro`.

## 9. Files and multimodal inputs

Upload a file:

```bash
curl -F file=@sample.pdf -F purpose=assistants http://127.0.0.1:8000/v1/files
```

Use the returned file ID:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model": "gemini-2.5-pro",
    "messages": [{"role": "user", "content": "Summarize the uploaded file"}],
    "file_ids": ["file-REPLACE_ME"]
  }'
```

## 10. Models

Default models in `config.yaml.example`:

- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.0-flash`
- `gemini-1.5-pro`

List configured models:

```bash
curl http://127.0.0.1:8000/v1/models
```

Override models through an environment variable:

```bash
export GWA_MODELS="gemini-2.5-pro,gemini-2.5-flash"
```

## 11. Troubleshooting

### `/v1/chat/completions` returns 503

No enabled Gemini cookies are configured, or all configured accounts failed initialization.

Check accounts:

```bash
curl http://127.0.0.1:8000/admin/accounts
```

Then add cookies via `config.yaml`, `cookies/*.json`, `/admin/cookies`, or `/admin-ui`.

### Gemini login stops working

Google cookies can expire or be invalidated. Export fresh `__Secure-1PSID` and `__Secure-1PSIDTS` values and update the account.

### SDK says API key missing

Most SDKs require an API key string even if GWA auth is disabled. Set a placeholder:

```bash
export OPENAI_API_KEY="local"
```

### Browser or OpenWebUI cannot reach the server

Use the correct base URL:

- Same machine local server: `http://127.0.0.1:8000/v1`
- Docker on same machine: `http://127.0.0.1:8000/v1`
- Remote deployment: `https://YOUR_DOMAIN/v1`

### Do not commit secrets

Never commit:

- `config.yaml` containing real cookies
- `cookies/*.json`
- `.env`
- API keys or Google cookies pasted into docs or source files

These paths are intentionally ignored by `.gitignore` where appropriate.
