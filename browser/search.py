"""Testable search and cursor pagination, independent of the UI framework."""
from urllib.parse import urlencode, urlsplit, urlunsplit


def make_params(params):
    values = {}
    for key, value in params.items():
        if value is None or value == "" or value == []:
            continue
        values[key] = str(value).lower() if isinstance(value, bool) else value
    return urlencode(values, doseq=True)


def trusted_next_page(value, endpoint):
    if not value:
        return None
    try:
        parsed, expected = urlsplit(value), urlsplit(endpoint)
        valid_port = parsed.port in (None, 443)
    except (TypeError, ValueError):
        return None
    # The cursor URL comes from a remote response and receives authenticated headers.
    if parsed.scheme != "https" or parsed.hostname not in {"civitai.com", "civitai.red", expected.hostname}:
        return None
    if parsed.username or parsed.password or not valid_port or parsed.path.rstrip("/") != "/api/v1/models":
        return None
    return urlunsplit((expected.scheme, expected.netloc, expected.path, parsed.query, ""))


def search_page(state, params, direction, fetch, endpoint):
    query = make_params(params)
    first_url = endpoint.rstrip("?") + ("?" + query if query else "")
    previous = state or {}
    fresh = direction == "search" or previous.get("query") != first_url
    current = {"current_page": 0, "pages": [first_url], "query": first_url} if fresh else {
        "current_page": previous.get("current_page", 0), "pages": list(previous.get("pages") or [first_url]), "query": first_url,
    }
    index = current["current_page"]
    if not fresh and direction == "previous":
        index = max(0, index - 1)
    elif not fresh and direction == "next":
        index = min(index + 1, len(current["pages"]) - 1)
    response = fetch(current["pages"][index])
    if not isinstance(response, dict) or not isinstance(response.get("items"), list):
        raise ValueError("模型网站暂时没有返回有效结果，请稍后重试或检查网络设置。")
    next_url = trusted_next_page((response.get("metadata") or {}).get("nextPage"), endpoint)
    current["current_page"] = index
    current["pages"] = current["pages"][:index + 1]
    if next_url and next_url not in current["pages"]:
        current["pages"].append(next_url)
    return current, response, index > 0, len(current["pages"]) > index + 1
