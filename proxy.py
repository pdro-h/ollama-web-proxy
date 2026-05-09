import json
import requests
from flask import Flask, request, Response, jsonify
from duckduckgo_search import DDGS
 
# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434"
PROXY_PORT   = 11435
SEARCH_COUNT = 3       # number of web results to inject
# ─────────────────────────────────────────────────────────────────────────────
 
app = Flask(__name__)
 
 
def web_search(query: str) -> str:
    """Return top N DuckDuckGo results as plain text."""
    try:
        with DDGS() as ddg:
            results = list(ddg.text(query, max_results=SEARCH_COUNT))
        if not results:
            return ""
        return "\n\n".join(
            f"[{r.get('title', '')}]\n{r.get('body', '')}" for r in results
        )
    except Exception as e:
        print(f"[web_search] error: {e}")
        return ""
 
 
def inject_context(messages: list) -> list:
    """Prepend a system message with web search results based on the last user message."""
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    if not last_user:
        return messages
 
    print(f"[proxy] searching: {last_user[:80]}...")
    context = web_search(last_user)
    if not context:
        return messages
 
    system_msg = {
        "role": "system",
        "content": (
            "The following is real-time information retrieved from the web. "
            "Use it to complement your knowledge when answering the user.\n\n"
            f"{context}"
        ),
    }
 
    # Replace existing system message or prepend a new one
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = system_msg["content"] + "\n\n" + messages[0]["content"]
    else:
        messages.insert(0, system_msg)
 
    return messages
 
 
# ── /api/chat ─────────────────────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    data["messages"] = inject_context(data.get("messages", []))
 
    upstream = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=data,
        stream=True,
        timeout=120,
    )
 
    return Response(
        upstream.iter_content(chunk_size=None),
        status=upstream.status_code,
        content_type=upstream.headers.get("Content-Type", "application/json"),
    )
 
 
# ── /api/generate ─────────────────────────────────────────────────────────────
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "")
 
    print(f"[proxy] searching: {prompt[:80]}...")
    context = web_search(prompt)
    if context:
        data["prompt"] = (
            f"Real-time web context:\n{context}\n\n"
            f"User prompt:\n{prompt}"
        )
 
    upstream = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json=data,
        stream=True,
        timeout=120,
    )
 
    return Response(
        upstream.iter_content(chunk_size=None),
        status=upstream.status_code,
        content_type=upstream.headers.get("Content-Type", "application/json"),
    )
 
 
# ── Passthrough for everything else (models list, tags, etc.) ─────────────────
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def passthrough(path):
    url = f"{OLLAMA_URL}/{path}"
    resp = requests.request(
        method=request.method,
        url=url,
        json=request.get_json(silent=True),
        params=request.args,
        timeout=30,
    )
    try:
        return jsonify(resp.json()), resp.status_code
    except Exception:
        return Response(resp.content, status=resp.status_code)
 
 
# ── Root health check ─────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ollama-web-proxy running", "port": PROXY_PORT})
 
 
if __name__ == "__main__":
    print(f"[proxy] Listening on port {PROXY_PORT}")
    print(f"[proxy] Forwarding to Ollama at {OLLAMA_URL}")
    print(f"[proxy] Web search: ON ({SEARCH_COUNT} results per query)")
    app.run(host="0.0.0.0", port=PROXY_PORT)
 