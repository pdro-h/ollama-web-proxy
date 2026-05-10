import re
import requests
from flask import Flask, request, Response, jsonify
from ddgs import DDGS

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434"
PROXY_PORT   = 11435
SEARCH_COUNT = 3
OLLAMA_MODEL = "qwen2.5-coder:14b"

# Only skip this one — it's a pure metadata request, not answer generation
SKIP_IF_STARTS_WITH = (
    "analyze this search query and provide",
)
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)

@app.after_request
def cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return Response(status=200)


def extract_query(text: str) -> str | None:
    """Extract the real user question from any Copilot prompt format."""
    lowered = text.strip().lower()

    # Skip salient terms metadata request
    if any(lowered.startswith(p) for p in SKIP_IF_STARTS_WITH):
        return None

    # Request 1 — conversation summarization: extract Follow Up Input
    if "follow up input:" in lowered:
        match = re.search(r"follow up input:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Request 3 — answer generation: extract question after context block
    if "answer the question based only" in lowered:
        match = re.search(r"</retrieved_document>\s*(.+)", text, re.IGNORECASE | re.DOTALL)
        if match:
            q = match.group(1).strip()
            if q and len(q) < 500:
                return q
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return lines[-1] if lines else None

    # Any other prompt — extract last meaningful line as query
    lines = [l.strip() for l in text.splitlines() if l.strip() and len(l.strip()) > 10]
    if lines:
        # Prefer shorter lines (more likely to be the actual question)
        candidates = [l for l in lines if len(l) < 200]
        return candidates[-1] if candidates else lines[-1]

    return None


def extract_vault_context(text: str) -> str:
    """Extrai apenas o conteúdo do vault do prompt do Copilot."""
    match = re.search(r"<retrieved_document>(.*?)</retrieved_document>", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def reformulate_query(text: str, context: str = "") -> str:
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json={
            "model": OLLAMA_MODEL,
            "prompt": (
                "You are a pentesting assistant. "
                "Based on the user's question and the vault context below, "
                "extract a concise web search query (max 10 words). "
                "Focus on: specific software names, versions, CVEs, or exploit techniques. "
                "Return ONLY the search query, nothing else.\n\n"
                f"Vault context:\n{context[:1000]}\n\n"
                f"User question: {text}"
            ),
            "stream": False
        }, timeout=30)
        return resp.json().get("response", text).strip()
    except Exception as e:
        print(f"[reformulate] error: {e}")
        return text  # fallback para a query original


def web_search(query: str) -> str:
    try:
        results = DDGS().text(query, max_results=SEARCH_COUNT)
        if not results:
            return ""
        return "\n\n".join(
            f"[{r.get('title', '')}]\n{r.get('body', '')}" for r in results
        )
    except Exception as e:
        print(f"[web_search] error: {e}")
        return ""


def inject_context(messages: list) -> list:
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    if not last_user:
        return messages

    query = extract_query(last_user)
    if not query:
        print(f"[proxy] skip: {last_user[:80]!r}")
        return messages

    vault_ctx = extract_vault_context(last_user)
    refined = reformulate_query(query, context=vault_ctx or last_user)
    print(f"[proxy] original:  {query[:80]!r}")
    print(f"[proxy] vault ctx: {vault_ctx[:80]!r}")
    print(f"[proxy] refined:   {refined[:80]!r}")
    context = web_search(refined)

    if not context:
        print("[proxy] no results")
        return messages

    print(f"[proxy] injecting {len(context)} chars of web context")

    web_block = (
        "[WEB SEARCH RESULTS - prioritize this over vault context for current exploit details]\n\n"
        f"{context}\n\n---\n\n"
    )

    for i in reversed(range(len(messages))):
        if messages[i].get("role") == "user":
            messages[i]["content"] = web_block + messages[i]["content"]
            break

    return messages


def do_chat():
    data = request.get_json(force=True)
    data["messages"] = inject_context(data.get("messages", []))
    upstream = requests.post(f"{OLLAMA_URL}/api/chat", json=data, stream=True, timeout=120)
    return Response(upstream.iter_content(chunk_size=None),
                    status=upstream.status_code,
                    content_type=upstream.headers.get("Content-Type", "application/json"))


def do_passthrough(path):
    url = f"{OLLAMA_URL}/{path}"
    resp = requests.request(method=request.method, url=url,
                            json=request.get_json(silent=True),
                            params=request.args, timeout=30)
    try:
        return jsonify(resp.json()), resp.status_code
    except Exception:
        return Response(resp.content, status=resp.status_code)


@app.route("/api/chat", methods=["POST"])
@app.route("/v1/api/chat", methods=["POST"])
def chat():
    return do_chat()

@app.route("/api/generate", methods=["POST"])
@app.route("/v1/api/generate", methods=["POST"])
def generate():
    return do_chat()

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ollama-web-proxy running", "port": PROXY_PORT})

@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/v1/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def passthrough(path):
    return do_passthrough(path)


if __name__ == "__main__":
    print(f"[proxy] Listening on port {PROXY_PORT}")
    print(f"[proxy] Forwarding to Ollama at {OLLAMA_URL}")
    print(f"[proxy] Web search: ON ({SEARCH_COUNT} results per query)")
    app.run(host="0.0.0.0", port=PROXY_PORT)