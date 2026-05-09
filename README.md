# ollama-web-proxy
 
Transparent proxy between **Obsidian Copilot** and **Ollama** that automatically injects real-time web search context into every request — no plugins, no Docker, no paid plans.
 
```
Obsidian Copilot → localhost:11435 (proxy) → DuckDuckGo → localhost:11434 (Ollama)
```
 
## How it works
 
Every message you send through Copilot is intercepted by the proxy, which:
 
1. Extracts your question
2. Searches DuckDuckGo for real-time results
3. Injects the results as a system message
4. Forwards the enriched request to Ollama
5. Streams the response back transparently
The model receives fresh web context alongside your vault notes on every query.
 
## Requirements
 
- Python 3.8+
- Ollama running locally
## Install
 
```bash
pip install flask duckduckgo-search requests
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
 
In Copilot Settings, change the Ollama base URL from:
 
```
http://localhost:11434
```
 
to:
 
```
http://localhost:11435
```
 
That's it. Your model now has internet access on every query.
 
## Configuration
 
Edit the top of `proxy.py` to adjust:
 
| Variable       | Default                  | Description                        |
|----------------|--------------------------|------------------------------------|
| `OLLAMA_URL`   | `http://localhost:11434` | Your Ollama instance URL           |
| `PROXY_PORT`   | `11435`                  | Port this proxy listens on         |
| `SEARCH_COUNT` | `3`                      | Number of web results to inject    |
 
## Run on startup (Windows)
 
Create a `start_proxy.bat`:
 
```bat
@echo off
python C:\path\to\proxy.py
```
 
Add it to Task Scheduler or your startup folder (`shell:startup`).
 
## Why this instead of alternatives?
 
| Option              | Docker | Paid | Auditable |
|---------------------|--------|------|-----------|
| Khoj                | ✅ yes  | ❌ no | ✅ yes    |
| Copilot Plus        | ❌ no   | ✅ yes | ❌ no    |
| open-obsidian-copilot | ❌ no | ❌ no | ⚠️ fork  |
| **ollama-web-proxy** | ❌ no  | ❌ no | ✅ yes   |
 
## License
 
MIT
 