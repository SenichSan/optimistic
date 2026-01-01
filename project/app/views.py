from django.http import HttpResponse
from django.urls import reverse


def robots_txt(request):
    # Build absolute URL to the sitemap index
    sitemap_url = request.build_absolute_uri(
        reverse('django.contrib.sitemaps.views.sitemap')
    )
    disallow_paths = [
        "/admin/",
        "/__debug__/",
        "/tinymce/",
        "/cart/",
        "/orders/",
        "/user/",
        "/catalog/search/",
    ]
    ru_disallow_paths = ["/ru" + p for p in disallow_paths]

    query_rules = [
        "/*?*q=",
        "/*?*order_by=",
        "/*?*on_sale=",
        "/*?*species=",
        "/*?*page=",
    ]
    ru_query_rules = ["/ru" + r for r in query_rules]

    lines = ["User-agent: *", "Disallow:"]
    lines.extend([f"Disallow: {p}" for p in disallow_paths + ru_disallow_paths])
    lines.extend([f"Disallow: {r}" for r in query_rules + ru_query_rules])
    lines.append(f"Sitemap: {sitemap_url}")
    return HttpResponse("\n".join(lines), content_type="text/plain")
