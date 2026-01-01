from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ManifestStaticFilesStorageLoose(ManifestStaticFilesStorage):
    """
    Same as Django's ManifestStaticFilesStorage but does not fail hard when a
    referenced file (e.g., *.map, legacy image URL in CSS) is missing.

    This keeps filename hashing for cache-busting, but if a referenced asset
    isn't present in the manifest, it will fall back to the original URL
    instead of raising ValueError during collectstatic post-processing.
    """

    manifest_strict = False


class ManifestStaticFilesStorageNoPostProcess(ManifestStaticFilesStorage):
    """
    Keep manifest hashing for top-level files, but disable CSS/JS URL
    rewriting during collectstatic to avoid crashes on legacy/broken
    references inside CSS (e.g., missing images or sourcemaps).
    """

    # Do not try to rewrite url(...) inside CSS or sourcemap hints
    patterns = ()
