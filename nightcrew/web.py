"""web_search + web_fetch for the agent (only when the Web switch is on in Settings).

Ollama's own web connection is used when OLLAMA_API_KEY is set (free key from
ollama.com/settings/keys): POST https://ollama.com/api/web_search and /api/web_fetch.
Without a key: DuckDuckGo's HTML results page for search, and a direct download +
readable-text extraction for fetch. Pages on private/local addresses are refused.
"""
from __future__ import annotations

import html
import ipaddress
import os
import re
import socket
from urllib.parse import parse_qs, unquote, urlparse

import httpx

UA = {"User-Agent": "Mozilla/5.0 (Eclipse local agent)"}
MAX_TEXT = 12_000
OLLAMA = "https://ollama.com/api"


def _key() -> str:
    """Windows Credential Manager / macOS Keychain first (set in Settings), then the env var."""
    try:
        import keyring
        k = keyring.get_password("eclipse", "ollama_api_key")
        if k:
            return k.strip()
    except Exception:
        pass
    return os.environ.get("OLLAMA_API_KEY", "").strip()


def set_key(key: str) -> bool:
    try:
        import keyring
        if key:
            keyring.set_password("eclipse", "ollama_api_key", key.strip())
        else:
            keyring.delete_password("eclipse", "ollama_api_key")
        return True
    except Exception:
        return False


def safe_url(url: str) -> str:
    """http(s) only, and never a private, loopback or link-local address (SSRF guard)."""
    u = urlparse(url if "://" in url else "https://" + url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError(f"not a web address: {url}")
    for info in socket.getaddrinfo(u.hostname, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError(f"refusing to fetch a local/private address: {u.hostname}")
    return u.geturl()


def to_text(page: str) -> str:
    """Readable text from HTML: trafilatura when installed, else a tag stripper."""
    try:
        import trafilatura
        t = trafilatura.extract(page, include_links=True, output_format="markdown")
        if t:
            return t
    except Exception:
        pass
    page = re.sub(r"(?is)<(script|style|noscript|svg|head).*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr)>", "\n", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()


def web_search(query: str, max_results: int = 5) -> str:
    n = max(1, min(int(max_results or 5), 10))
    if _key():
        r = httpx.post(OLLAMA + "/web_search", json={"query": query, "max_results": n},
                       headers={"Authorization": f"Bearer {_key()}"}, timeout=30)
        r.raise_for_status()
        rows = r.json().get("results", [])
        return "\n\n".join(f"{i}. {x.get('title', '')}\n   {x.get('url', '')}\n   {str(x.get('content', ''))[:400]}"
                           for i, x in enumerate(rows, 1)) or "(no results)"
    r = httpx.post("https://html.duckduckgo.com/html/", data={"q": query}, headers=UA, timeout=20, follow_redirects=True)
    out = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', r.text, re.S):
        href = m.group(1)
        if "uddg=" in href:
            href = unquote(parse_qs(urlparse(href).query).get("uddg", [href])[0])
        title, snip = (html.unescape(re.sub("<[^>]+>", "", g)).strip() for g in (m.group(2), m.group(3)))
        out.append(f"{len(out) + 1}. {title}\n   {href}\n   {snip[:300]}")
        if len(out) >= n:
            break
    return "\n\n".join(out) or "(no results)"


def web_fetch(url: str) -> str:
    if _key():
        r = httpx.post(OLLAMA + "/web_fetch", json={"url": url}, headers={"Authorization": f"Bearer {_key()}"}, timeout=40)
        r.raise_for_status()
        d = r.json()
        text = d.get("content", "")
        return (f"# {d.get('title', '')}\n{url}\n\n" + text)[:MAX_TEXT]
    url = safe_url(url)
    # every hop (redirects too) is checked BEFORE it is requested
    hook = {"request": [lambda req: safe_url(str(req.url))]}
    with httpx.Client(headers=UA, timeout=25, follow_redirects=True, max_redirects=5, event_hooks=hook) as c:
        r = c.get(url)
    if "html" not in r.headers.get("content-type", "html"):
        return f"{url}\n\n" + r.text[:MAX_TEXT]
    return (f"{url}\n\n" + to_text(r.text))[:MAX_TEXT]


def _fn(name, desc, props, req):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": req}}}


SCHEMAS = [
    _fn("web_search", "Search the web. Returns titles, links and snippets. Then web_fetch the best link to read it.",
        {"query": {"type": "string"}, "max_results": {"type": "integer"}}, ["query"]),
    _fn("web_fetch", "Download a web page and return its readable text (markdown). Use it to read docs, articles, or scrape a page.",
        {"url": {"type": "string"}}, ["url"]),
]
REGISTRY = {"web_search": web_search, "web_fetch": web_fetch}
