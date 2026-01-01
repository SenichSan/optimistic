"""
SEO-friendly 301 redirects middleware and language activation by URL prefix.
"""
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from urllib.parse import urlencode, parse_qsl
from django.urls import resolve, Resolver404
from django.utils import translation
from goods.models import Products


class ProductURLRedirectMiddleware:
    """
    Redirect old product URLs to new structure:
    /catalog/product/<slug>/ → /<category>/<product>/
    
    This preserves SEO authority (301 redirect passes 90-99% of link equity).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is an old product URL
        path = request.path
        
        # Match pattern: /catalog/product/<slug>/
        if path.startswith('/catalog/product/'):
            # Extract product slug
            slug = path.replace('/catalog/product/', '').rstrip('/')
            
            if slug:
                try:
                    # Find product by slug
                    product = Products.objects.select_related('category').get(slug=slug)
                    # Generate new URL
                    new_url = product.get_absolute_url()
                    # Preserve query string if present
                    if request.META.get('QUERY_STRING'):
                        new_url += '?' + request.META['QUERY_STRING']
                    # Return 301 redirect
                    return HttpResponsePermanentRedirect(new_url)
                except Products.DoesNotExist:
                    # Product not found, let Django handle 404
                    pass
        
        # Continue normal processing
        response = self.get_response(request)
        return response


class LanguagePrefixMiddleware:
    """
    Activate language based on URL prefix.
    Rules:
    - Default language is 'uk' and has NO prefix.
    - Russian ('ru') must have '/ru' prefix.

    This middleware sets the active language for the request context so
    templates using `{% get_current_language %}` and `{% trans %}` behave correctly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path or "/"

        # Bypass for assets/admin/debug
        if path.startswith(("/static/", "/media/", "/admin/", "/__debug__/", "/tinymce/")):
            return self.get_response(request)

        # Serve sitemap/robots without language cookies/headers for better cacheability
        if path in ("/sitemap.xml", "/robots.txt"):
            response = self.get_response(request)
            # Add light cache headers if not present (harmless if overwritten downstream)
            try:
                response.headers.setdefault("Cache-Control", "public, max-age=3600")
                response.headers.setdefault("X-Content-Type-Options", "nosniff")
            except Exception:
                pass
            return response

        cookie_lang = request.COOKIES.get("site_lang", "")

        # Helper: drop 'lang' param from query string while keeping others
        def _qs_without_lang() -> str:
            raw = request.META.get('QUERY_STRING', '')
            if not raw:
                return ''
            pairs = [(k, v) for k, v in parse_qsl(raw, keep_blank_values=True) if k.lower() != 'lang']
            return urlencode(pairs, doseq=True)

        # Explicit switch via ?lang=uk|ru has priority over cookie
        qlang = request.GET.get('lang')
        if qlang in ("uk", "ru"):
            desired = qlang
            # Compute target path according to desired language
            if desired == 'ru':
                if not (path == "/ru" or path.startswith("/ru/")):
                    target = "/ru" + (path if path.startswith('/') else '/' + path)
                else:
                    target = path
            else:  # desired == 'uk'
                if path == "/ru":
                    target = "/"
                elif path.startswith("/ru/"):
                    target = path[3:] or "/"
                else:
                    target = path

            # Build redirect URL without ?lang, preserve other params
            qs = _qs_without_lang()
            if qs:
                target = f"{target}?{qs}"

            # Activate and set cookie on a lightweight redirect response
            translation.activate(desired)
            resp = HttpResponseRedirect(target)
            try:
                resp.set_cookie("site_lang", desired, max_age=60*60*24*30, samesite='Lax')
                resp.headers.setdefault("Content-Language", desired)
                # Prevent caching of the language-switch redirect itself
                resp.headers.setdefault("Cache-Control", "no-store, no-cache, must-revalidate")
                resp.headers.setdefault("Pragma", "no-cache")
            except Exception:
                pass
            return resp

        # Determine language from path prefix
        if path == "/ru" or path.startswith("/ru/"):
            lang = "ru"
            # Strip '/ru' prefix for URL resolving
            stripped = path[3:] or "/"
            try:
                request.path_info = stripped
                if isinstance(request.META, dict):
                    request.META['PATH_INFO'] = stripped
            except Exception:
                pass
        else:
            lang = "uk"
            # Best practice: do not auto-redirect by cookie; language is defined by URL only.
            # Keep 302 redirects ONLY for explicit switches via `?lang=...` above.

        # Activate for current request lifecycle
        translation.activate(lang)
        request.LANGUAGE_CODE = lang

        response = self.get_response(request)

        # Persist cookie to current language (30 days)
        try:
            response.set_cookie("site_lang", lang, max_age=60*60*24*30, samesite='Lax')
            response.headers.setdefault("Content-Language", lang)
        except Exception:
            pass

        return response
