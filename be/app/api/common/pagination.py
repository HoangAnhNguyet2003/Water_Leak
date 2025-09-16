
from urllib.parse import urlencode

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

def parse_pagination(args):
    try:
        page = int(args.get("page", DEFAULT_PAGE))
    except Exception:
        page = DEFAULT_PAGE
    page = max(page, 1)

    try:
        page_size = int(args.get("page_size", DEFAULT_PAGE_SIZE))
    except Exception:
        page_size = DEFAULT_PAGE_SIZE
    page_size = min(max(page_size, 1), MAX_PAGE_SIZE)

    return page, page_size

def build_links(base_path: str, page: int, page_size: int, has_next: bool, extra_params: dict | None = None):
    extra_params = extra_params or {}
    links = []
    q_self = urlencode({**extra_params, "page": page, "page_size": page_size})
    links.append(f'<{base_path}?{q_self}>; rel="self"')
    if page > 1:
        q_prev = urlencode({**extra_params, "page": page-1, "page_size": page_size})
        links.append(f'<{base_path}?{q_prev}>; rel="prev"')
    if has_next:
        q_next = urlencode({**extra_params, "page": page+1, "page_size": page_size})
        links.append(f'<{base_path}?{q_next}>; rel="next"')
    return ", ".join(links)
