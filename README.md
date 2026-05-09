# ollama-web-proxy
 
Transparent proxy between **Obsidian Copilot** and **Ollama** that automatically injects real-time web search context into every request — no plugins, no Docker, no paid plans.
 
```
Obsidian Copilot → localhost:11435 (proxy) → DuckDuckGo → localhost:11434 (Ollama)
```
 
## How it works
 
Every message you send through Copilot is intercepted by the proxy, which:
 
1. Extracts your real question from Copilot's internal prompt formats
2. Searches DuckDuckGo for real-time results
3. Injects the results directly into the request before the vault context
4. Forwards the enriched request to Ollama
5. Streams the response back transparently
The model receives fresh web context alongside your vault notes on every query.
 
## Requirements
 
- Python 3.8+
- Ollama running locally
- Obsidian with the [Copilot plugin](https://github.com/logancyang/obsidian-copilot)
## Install
 
```bash
pip install flask ddgs requests
```
 
## Run
 
```bash
python proxy.py
```
 
You should see:
 
```
[proxy] Listening on port 11435
[proxy] Forwarding to Ollama at http://localhost:11434
[proxy] Web search: ON (3 results per query)
```
 
## Configure Obsidian Copilot
 
In Copilot Settings → Model → edit your Ollama model → **Base URL**:
 
```
http://localhost:11435/v1/
```
 
That's it. Your model now has internet access on every query.
 
## Configuration
 
Edit the top of `proxy.py`:
 
| Variable       | Default                  | Description                     |
|----------------|--------------------------|---------------------------------|
| `OLLAMA_URL`   | `http://localhost:11434` | Your Ollama instance URL        |
| `PROXY_PORT`   | `11435`                  | Port this proxy listens on      |
| `SEARCH_COUNT` | `3`                      | Number of web results to inject |
 
## Run on startup (Windows)
 
Create a `start_proxy.bat`:
 
```bat
@echo off
cd /d C:\path\to\ollama-web-proxy
call venv\Scripts\activate
python proxy.py
```
 
Add it to your startup folder (`Win + R` → `shell:startup`).
 
## Why this instead of alternatives?
 
| Option               | Docker | Paid  | Auditable |
|----------------------|--------|-------|-----------|
| Khoj                 | ✅ yes  | ❌ no  | ✅ yes    |
| Copilot Plus         | ❌ no   | ✅ yes | ❌ no     |
| open-obsidian-copilot| ❌ no   | ❌ no  | ⚠️ fork   |
| **ollama-web-proxy** | ❌ no   | ❌ no  | ✅ yes    |
 
## Recommended models
 
Works with any Ollama model, but larger models follow injected context better.
Tested with `qwen2.5-coder:14b`.
 
## License
 
MIT
 