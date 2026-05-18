# gemini-web-api (GWA)

A FastAPI middleware/proxy that exposes Gemini Web through OpenAI-compatible, Claude-compatible, and native Gemini-style HTTP APIs. It uses HanaokaYuzu's `gemini_webapi` as the core runtime and keeps protocol routers, account pooling, prompt conversion, streaming adapters, and admin operations separated.

## Features

- OpenAI-compatible `/v1/chat/completions` with streaming and non-streaming responses
- Claude-compatible `/v1/messages` and `/anthropic/v1/messages`
- Model listing via `/v1/models` and `/v1beta/models`
- Native Gemini-style `/gemini/generate`
- File upload endpoint compatible with OpenAI-style `/v1/files`
- Multiple Gemini cookie accounts with round-robin rotation
- Tool/function call extraction from Gemini JSON responses
- Temporary chat mode, model selection, CORS, request IDs, rate limiting, API keys
- Admin endpoints plus a small `/admin-ui` HTML helper
- Docker and docker-compose ready

## Project layout

```text
app/
  main.py             FastAPI app and router registration
  config.py           YAML/env configuration loader
  dependencies.py     FastAPI dependency accessors
  middleware.py       request ID, API key, and rate-limit middleware
core/
  account_pool.py     multi-cookie account loading and rotation
  gemini_client.py    gemini_webapi client lifecycle manager
  prompt_compat.py    OpenAI/Claude prompt normalization
  stream_adapter.py   SSE adapters for OpenAI/Claude streams
  tool_adapter.py     Gemini JSON → tool call conversion
  history.py          upload/file store
routers/
  openai.py           OpenAI-compatible endpoints
  claude.py           Claude-compatible endpoints
  gemini.py           Native Gemini-style endpoints
  admin.py            cookie/account admin endpoints
models/
  schemas.py          request/response schemas
admin/
  index.html          small browser admin helper
```

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` to check the server.

## Configure Gemini cookies

Provide Gemini Web cookies using either `config.yaml`, JSON files in `cookies/`, or the admin endpoint.

`config.yaml` example:

```yaml
gemini:
  cookies:
    - id: personal
      secure_1psid: "YOUR __Secure-1PSID"
      secure_1psidts: "YOUR __Secure-1PSIDTS IF PRESENT"
      enabled: true
```

Cookie JSON file example at `cookies/personal.json`:

```json
{
  "id": "personal",
  "secure_1psid": "YOUR __Secure-1PSID",
  "secure_1psidts": "YOUR __Secure-1PSIDTS IF PRESENT",
  "enabled": true
}
```

Runtime admin API:

```bash
curl -X POST http://127.0.0.1:8000/admin/cookies \
  -H 'content-type: application/json' \
  -d '{"id":"personal","secure_1psid":"...","secure_1psidts":"..."}'
```

## OpenAI SDK example

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="local")

response = client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Say hello from Gemini Web"}],
)
print(response.choices[0].message.content)
```

Streaming:

```python
for chunk in client.chat.completions.create(
    model="gemini-2.5-pro",
    messages=[{"role": "user", "content": "Stream a short poem"}],
    stream=True,
):
    print(chunk.choices[0].delta.content or "", end="")
```

## Claude-compatible example

```bash
curl http://127.0.0.1:8000/v1/messages \
  -H 'content-type: application/json' \
  -d '{
    "model": "gemini-2.5-pro",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## File uploads

```bash
curl -F file=@sample.pdf -F purpose=assistants http://127.0.0.1:8000/v1/files
```

Use the returned `id` in `file_ids` on chat, Claude, or native Gemini requests.

## Docker

```bash
cp config.yaml.example config.yaml
docker compose up --build
```

The compose file mounts `cookies/`, `uploads/`, and `gemini_cookies/` so cookie refreshes and uploads survive container restarts.

## Environment variables

- `GWA_CONFIG` path to config YAML, default `config.yaml`
- `GWA_API_KEYS` comma-separated API keys; empty disables auth for local testing
- `GWA_CORS_ORIGINS` comma-separated CORS origins
- `GWA_DEFAULT_MODEL` default model name
- `GWA_MODELS` comma-separated model list
- `GWA_COOKIES_DIR` cookie JSON directory
- `GWA_UPLOAD_DIR` upload directory
- `GWA_TEMPORARY_CHAT` default temporary mode (`true`/`false`)

## Production notes

- Configure `GWA_API_KEYS` in production.
- Use dedicated Gemini browser sessions for cookies.
- Mount persistent `cookies/` and `gemini_cookies/` directories.
- The Gemini Web API is a reverse-engineered web interface; monitor account limits and failures through `/admin/accounts`.
