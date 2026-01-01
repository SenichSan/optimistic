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
    # Whitelist query parameters to keep in canonical URL
    raw_qs = request.META.get('QUERY_STRING', '')
    allowed = {'page', 'species'}
    pairs = [(k, v) for k, v in parse_qsl(raw_qs, keep_blank_values=False) if k in allowed]
    qs = urlencode(pairs, doseq=True)
    return _abs_uri(request, request.path, qs)


@register.simple_tag(takes_context=True)
def switch_lang_url(context, lang_code: str) -> str:
    """Return relative URL for current page with explicit '?lang=..' parameter.
    The middleware consumes this param, updates cookie, redirects to correct URL, and removes the param.
    Other query params are preserved.
    """
    request = context.get('request')
    if not request:
        return '/?lang=' + (lang_code or 'uk')
    from urllib.parse import urlencode, parse_qsl
    raw = request.META.get('QUERY_STRING', '')
    pairs = [(k, v) for k, v in parse_qsl(raw, keep_blank_values=True) if k.lower() != 'lang']
    pairs.append(('lang', lang_code))
    qs = urlencode(pairs, doseq=True)
    return request.path + ('?' + qs if qs else '')
