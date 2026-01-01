from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from django import template

register = template.Library()


def _abs_uri(request, path: str, query: str = '') -> str:
    """Build absolute URL for given path using current request host and scheme.
    Optionally append query string (without leading '?').
    """
    base = request.build_absolute_uri('/')
    parts = urlsplit(base)
    # Ensure single leading slash
    norm_path = '/' + path.lstrip('/')
    norm_query = (query or '').lstrip('?')
    return urlunsplit((parts.scheme, parts.netloc, norm_path, norm_query, ''))


def _to_lang_path(path: str, lang: str) -> str:
    """Return path adjusted for target lang with default language 'uk' having no prefix."""
    # Normalize
    if not path:
        path = '/'
    if not path.startswith('/'):
        path = '/' + path

    is_ru = path.startswith('/ru/') or path == '/ru'

    if lang == 'uk':
        # UK should be without prefix: strip leading /ru
        if is_ru:
            # remove only the first "/ru" segment
            stripped = path[3:]  # remove '/ru'
            if not stripped:
                stripped = '/'
            return stripped if stripped.startswith('/') else '/' + stripped
        return path

    if lang == 'ru':
        # RU should have /ru prefix exactly once
        if is_ru:
            return path
        # avoid double slashes
        return '/ru' + (path if path.startswith('/') else '/' + path)

    # Fallback: return original
    return path


@register.simple_tag(takes_context=True)
def alternate_url(context, lang_code: str) -> str:
    """Return absolute URL of the current page in the specified language (uk or ru)."""
    request = context.get('request')
    if not request:
        return ''
    alt_path = _to_lang_path(request.path, lang_code)
    return _abs_uri(request, alt_path)


@register.simple_tag(takes_context=True)
def canonical_url(context) -> str:
    """Return canonical absolute URL for current language (ignore query params)."""
    request = context.get('request')
    if not request:
        return ''
    # Start from current path
    path = request.path or '/'

    # Detect RU prefix and work on language-agnostic path
    is_ru = path == '/ru' or path.startswith('/ru/')
    def _strip_ru(p: str) -> str:
        if is_ru:
            p = p[3:] or '/'
        return p
    def _add_ru(p: str) -> str:
        if is_ru:
            return '/ru' + (p if p.startswith('/') else '/' + p)
        return p

    langless_path = _strip_ru(path)

    # 1) Normalize '/catalog/all/' to '/catalog/'
    if langless_path.rstrip('/') == '/catalog/all':
        langless_path = '/catalog/'

    # 2) Build canonical query
    raw_qs = request.META.get('QUERY_STRING', '')
    allowed = {'page', 'species'}
    pairs = []
    drop_species_cubensis = langless_path.rstrip('/') == '/catalog/sporovi-vidbitki'
    for k, v in parse_qsl(raw_qs, keep_blank_values=False):
        if k not in allowed:
            continue
        # Drop page=1 from canonical
        if k == 'page' and (v is None or v == '' or v == '1'):
            continue
        # For sporovi-vidbitki, default species=cubensis is canonical without the param
        if drop_species_cubensis and k == 'species' and (v or '').lower() == 'cubensis':
            continue
        pairs.append((k, v))

    qs = urlencode(pairs, doseq=True)
    canon_path = _add_ru(langless_path)
    return _abs_uri(request, canon_path, qs)
