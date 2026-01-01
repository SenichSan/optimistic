import os
from io import BytesIO
from typing import Tuple, Literal

from PIL import Image, ImageFilter

try:
    import pillow_avif  # noqa: F401  # registers AVIF
    AVIF_AVAILABLE = True
except Exception:
    AVIF_AVAILABLE = False


def ensure_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def _open_image(path: str) -> Image.Image:
    img = Image.open(path)
    img.load()
    return img


def _fit_box(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    # cover-like resize with center crop to exact size
    target_w, target_h = size
    src_w, src_h = img.size
    src_ratio = src_w / src_h if src_h else 1
    tgt_ratio = target_w / target_h if target_h else 1

    if src_ratio > tgt_ratio:
        # source wider -> fit height then crop width
        new_h = target_h
        new_w = int(round(new_h * src_ratio))
    else:
        # source taller -> fit width then crop height
        new_w = target_w
        new_h = int(round(new_w / src_ratio))

    resized = img.convert("RGBA").resize((new_w, new_h), Image.LANCZOS)
    # crop center
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    box = (left, top, left + target_w, top + target_h)
    return resized.crop(box)


def _fit_box_contain(img: Image.Image, size: Tuple[int, int], background=(0, 0, 0, 0)) -> Image.Image:
    """Resize to fit entirely inside target box without cropping.
    The remaining area is filled with transparent (default) background.
    """
    target_w, target_h = size
    src_w, src_h = img.size
    if src_w == 0 or src_h == 0 or target_w == 0 or target_h == 0:
        return img.copy()

    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))

    base = Image.new("RGBA", (target_w, target_h), background)
    resized = img.convert("RGBA").resize((new_w, new_h), Image.LANCZOS)

    left = (target_w - new_w) // 2
    top = (target_h - new_h) // 2
    base.paste(resized, (left, top), resized if resized.mode == "RGBA" else None)
    return base


def save_webp(img: Image.Image, out_path: str, quality: int = 80) -> None:
    ensure_dir(out_path)
    img.save(out_path, format="WEBP", quality=quality, method=6)


def save_avif(img: Image.Image, out_path: str, quality: int = 50) -> None:
    if not AVIF_AVAILABLE:
        return
    ensure_dir(out_path)
    # pillow-avif uses 'quality' 0..100 similar to JPEG; smaller -> worse
    # we'll map requested 'quality' ~ cqLevel analogue
    img.save(out_path, format="AVIF", quality=quality)


def save_avif_optimized(img: Image.Image, out_path: str, image_type: str = "background", quality: int | None = None) -> None:
    """
    Optimized AVIF saver expected by management commands.
    Chooses sensible defaults depending on image type.

    image_type:
      - 'background' -> aggressive compression for large backdrops
      - 'product'    -> conservative to preserve detail
    """
    if not AVIF_AVAILABLE:
        return

    # Normalize type
    kind = (image_type or "background").strip().lower()

    # If quality explicitly provided (e.g., via management command), honor it
    if isinstance(quality, int) and 0 <= quality <= 100:
        q = quality
    else:
        # Heuristic presets (tuned for pillow-avif quality scale)
        if kind == "product":
            # Preserve detail on product shots a bit more than before
            q = 45
        else:
            # Backgrounds: adapt by size; larger backgrounds need higher quality to avoid mushy look
            longest = max(getattr(img, 'size', (0, 0)) or (0, 0))
            if longest >= 2400:
                q = 66
            elif longest >= 1920:
                q = 62
            elif longest >= 1600:
                q = 58
            else:
                q = 54

    save_avif(img, out_path, quality=q)


def build_variant_paths(original_path: str, size_name: str, out_ext: str) -> str:
    # /media/categories/foo.png -> /media/categories/foo_<size>.<ext>
    root, _ext = os.path.splitext(original_path)
    return f"{root}_{size_name}.{out_ext}"


def generate_icon_variants(
    original_fs_path: str,
    size: Tuple[int, int] = (128, 128),
    mode: Literal["contain", "cover"] = "contain",
    quality_avif: int | None = None,
    quality_webp: int | None = None,
) -> dict:
    """
    Generate WebP and AVIF variants next to original file.
    Returns dict with keys: 'webp', 'avif' (values are absolute FS paths that exist).
    Missing formats may be absent if plugin not available.
    """
    if not original_fs_path or not os.path.exists(original_fs_path):
        return {}

    img = _open_image(original_fs_path)
    if mode == "cover":
        fitted = _fit_box(img, size)
    else:
        fitted = _fit_box_contain(img, size)

    size_name = f"{size[0]}x{size[1]}"

    out = {}

    webp_q = int(quality_webp) if isinstance(quality_webp, int) else 82
    webp_path = build_variant_paths(original_fs_path, size_name, "webp")
    save_webp(fitted, webp_path, quality=webp_q)
    if os.path.exists(webp_path):
        out["webp"] = webp_path

    if AVIF_AVAILABLE:
        avif_q = int(quality_avif) if isinstance(quality_avif, int) else 70
        avif_path = build_variant_paths(original_fs_path, size_name, "avif")
        save_avif(fitted, avif_path, quality=avif_q)
        if os.path.exists(avif_path):
            out["avif"] = avif_path

    return out


def _resize_cover(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    """Resize to fully cover target box, cropping overflow (no canvas)."""
    target_w, target_h = size
    src_w, src_h = img.size
    if not src_w or not src_h:
        return img.copy()
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (max(1, int(round(src_w * scale))), max(1, int(round(src_h * scale))))
    return img.convert("RGBA").resize(new_size, Image.LANCZOS)


def _blur_extend_canvas(img: Image.Image, size: Tuple[int, int], blur_radius: int = 24) -> Image.Image:
    """Make a canvas of size WxH with a blurred cover background from img and a contained sharp foreground.
    Useful for horizontal card canvases when the source is vertical — prevents awkward crops.
    """
    target_w, target_h = size
    # Background: cover + blur
    bg = _resize_cover(img, size)
    # center-crop to exact size
    left = max(0, (bg.width - target_w) // 2)
    top = max(0, (bg.height - target_h) // 2)
    bg = bg.crop((left, top, left + target_w, top + target_h)).filter(ImageFilter.GaussianBlur(blur_radius))

    # Foreground: contain, centered
    fg = _fit_box_contain(img, size)

    # Composite: paste foreground over blurred background
    out = Image.new("RGBA", (target_w, target_h))
    out.paste(bg, (0, 0))
    out.alpha_composite(fg if fg.mode == "RGBA" else fg.convert("RGBA"))
    return out


def generate_card_variants(
    original_fs_path: str,
    size_desktop: Tuple[int, int] = (230, 160),
    size_mobile: Tuple[int, int] = (200, 160),
    background_blur: bool = True,
    quality_webp: int | None = None,
    quality_avif: int | None = None,
) -> dict:
    """Generate AVIF/WebP card variants (desktop+mobile) with blur-extend canvas.
    Returns dict of created paths per size: {'230x160': {'webp': path, 'avif': path}, '200x160': {...}}
    """
    if not original_fs_path or not os.path.exists(original_fs_path):
        return {}

    img = _open_image(original_fs_path)
    sizes = [size_desktop, size_mobile]
    result = {}
    for w, h in sizes:
        size_name = f"{w}x{h}"
        # If blur-extend is disabled, use cover-crop to fully fill canvas (no transparent side bars)
        canvas = _blur_extend_canvas(img, (w, h)) if background_blur else _fit_box(img, (w, h))

        out_webp = build_variant_paths(original_fs_path, size_name, "webp")
        out_avif = build_variant_paths(original_fs_path, size_name, "avif")

        # Save formats
        save_webp(canvas, out_webp, quality=int(quality_webp) if isinstance(quality_webp, int) else 82)
        if AVIF_AVAILABLE:
            save_avif(canvas, out_avif, quality=int(quality_avif) if isinstance(quality_avif, int) else 60)

        created = {}
        if os.path.exists(out_webp):
            created["webp"] = out_webp
        if AVIF_AVAILABLE and os.path.exists(out_avif):
            created["avif"] = out_avif
        result[size_name] = created

    return result


def generate_formats_noresize(
    original_fs_path: str,
    *,
    image_type: Literal["product", "background"] = "product",
    quality_avif: int | None = None,
    quality_webp: int | None = None,
    overwrite: bool = False,
) -> dict:
    """
    Create AVIF and WebP next to the original image WITHOUT resizing.
    Keeps alpha if present, preserves original canvas size, and writes:
      <root>.avif, <root>.webp (no size suffix)

    Returns dict with keys:
      {
        'original': '<path-to-original>',
        'avif': '<path-to-avif>' | None,
        'webp': '<path-to-webp>' | None,
        'mime_order': [('image/avif', avif_path), ('image/webp', webp_path), ('image/jpeg', original) | ('image/png', original)]
      }
    """
    if not original_fs_path or not os.path.exists(original_fs_path):
        return {}

    root, ext = os.path.splitext(original_fs_path)
    ext_lower = (ext or "").lower()

    out_avif = f"{root}.avif"
    out_webp = f"{root}.webp"

    # Decide mime for original as fallback
    if ext_lower in (".jpg", ".jpeg"):
        original_mime = "image/jpeg"
    elif ext_lower == ".png":
        original_mime = "image/png"
    else:
        # default to jpeg to be safe in <img>
        original_mime = "image/jpeg"

    img = _open_image(original_fs_path)

    # Preserve transparency: keep RGBA/LA; convert palette to RGBA; fallback to RGB
    if img.mode == "P":
        img = img.convert("RGBA")
    if img.mode not in ("RGB", "RGBA", "LA"):
        img = img.convert("RGB")

    created_avif = None
    created_webp = None

    # Save AVIF
    if AVIF_AVAILABLE:
        if overwrite or (not os.path.exists(out_avif)):
            save_avif_optimized(img, out_avif, image_type=image_type, quality=quality_avif if isinstance(quality_avif, int) else None)
        if os.path.exists(out_avif):
            created_avif = out_avif

    # Save WebP
    webp_q = int(quality_webp) if isinstance(quality_webp, int) else (82 if image_type == "background" else 80)
    if overwrite or (not os.path.exists(out_webp)):
        save_webp(img, out_webp, quality=webp_q)
    if os.path.exists(out_webp):
        created_webp = out_webp

    mime_order = []
    if created_avif:
        mime_order.append(("image/avif", created_avif))
    if created_webp:
        mime_order.append(("image/webp", created_webp))
    mime_order.append((original_mime, original_fs_path))

    return {
        "original": original_fs_path,
        "avif": created_avif,
        "webp": created_webp,
        "mime_order": mime_order,
    }


def build_prioritized_picture_sources(original_fs_path: str) -> list[tuple[str, str]]:
    """
    Given a path to the original file, return a prioritized list of (mime, path)
    suitable to render inside <picture> as <source type=... srcset=...>, ending with
    the original as <img src=...> fallback. Does NOT perform generation; assumes
    `generate_formats_noresize()` was called or variants already exist.
    """
    if not original_fs_path:
        return []
    root, _ext = os.path.splitext(original_fs_path)
    avif = f"{root}.avif"
    webp = f"{root}.webp"

    sources: list[tuple[str, str]] = []
    if os.path.exists(avif):
        sources.append(("image/avif", avif))
    if os.path.exists(webp):
        sources.append(("image/webp", webp))

    # infer original mime
    ext_lower = _ext.lower()
    if ext_lower in (".jpg", ".jpeg"):
        original_mime = "image/jpeg"
    elif ext_lower == ".png":
        original_mime = "image/png"
    else:
        original_mime = "image/jpeg"
    sources.append((original_mime, original_fs_path))
    return sources
