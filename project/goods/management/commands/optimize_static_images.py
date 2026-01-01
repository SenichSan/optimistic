import os
import glob
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image
from common.image_utils import save_avif_optimized, save_webp, ensure_dir


class Command(BaseCommand):
    help = "Optimize static images (backgrounds, hero images) with aggressive AVIF compression"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be optimized without actually doing it',
        )
        parser.add_argument(
            '--only-backgrounds',
            action='store_true',
            help='Process only files detected as backgrounds (by filename patterns)',
        )
        parser.add_argument(
            '--only-products',
            action='store_true',
            help='Process only non-background images (opposite of --only-backgrounds)',
        )
        parser.add_argument(
            '--quality',
            type=int,
            default=12,
            help='AVIF quality for background images (default: 12)',
        )
        parser.add_argument(
            '--bg-quality',
            type=int,
            default=None,
            help='Override AVIF quality specifically for background images (takes priority over --quality)'
        )
        parser.add_argument(
            '--product-quality',
            type=int,
            default=None,
            help='Override AVIF quality specifically for product images (takes priority over --quality)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if AVIF files already exist',
        )
        parser.add_argument(
            '--bg-max-size',
            type=int,
            default=2400,
            help='Max longest side for background images (0 disables resize, default: 2400)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        only_backgrounds = options.get('only_backgrounds', False)
        only_products = options.get('only_products', False)
        quality = options['quality']
        bg_quality = options.get('bg_quality')
        product_quality = options.get('product_quality')
        force = options['force']
        bg_max_size = options.get('bg_max_size')

        if only_backgrounds and only_products:
            self.stderr.write(self.style.ERROR("Use only one of --only-backgrounds or --only-products"))
            return 1
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No files will be modified"))
        
        # Define static image directories to scan
        static_dirs = [
            os.path.join(settings.BASE_DIR, 'static'),
            os.path.join(settings.MEDIA_ROOT),
        ]
        
        # Image patterns to look for
        patterns = ['*.png', '*.jpg', '*.jpeg']
        
        # Files that should be treated as backgrounds (aggressive compression)
        background_patterns = [
            '*bg*', '*background*', '*hero*', '*banner*', 
            'seo-text-bg*', '*texture*', '*pattern*'
        ]
        
        total_processed = 0
        total_size_before = 0
        total_size_after = 0
        
        self.stdout.write(f"\n🔍 Scanning for static images to optimize...")
        
        for static_dir in static_dirs:
            if not os.path.exists(static_dir):
                continue
                
            self.stdout.write(f"\n📁 Scanning: {static_dir}")
            
            for pattern in patterns:
                search_pattern = os.path.join(static_dir, '**', pattern)
                files = glob.glob(search_pattern, recursive=True)
                
                for file_path in files:
                    try:
                        # Skip if already processed or is a variant
                        if any(suffix in file_path for suffix in ['_128.', '_400x300.', '_800x600.']):
                            continue
                        
                        # Skip problematic files
                        filename_lower = os.path.basename(file_path).lower()
                        if any(skip in filename_lower for skip in ['not found', 'baseavatar', 'temp', 'cache']):
                            continue
                            
                        # Get original file size
                        original_size = os.path.getsize(file_path)
                        total_size_before += original_size
                        
                        # Determine image type based on filename
                        filename = os.path.basename(file_path).lower()
                        is_background = any(pattern.replace('*', '') in filename 
                                          for pattern in background_patterns)

                        if only_backgrounds and not is_background:
                            continue
                        if only_products and is_background:
                            continue
                        
                        image_type = "background" if is_background else "product"
                        
                        # Generate optimized paths
                        root, ext = os.path.splitext(file_path)
                        avif_path = f"{root}.avif"
                        webp_path = f"{root}.webp"
                        
                        # Check if we need to process
                        needs_processing = not os.path.exists(avif_path) or force
                        
                        if not needs_processing:
                            existing_size = os.path.getsize(avif_path)
                            # If existing AVIF is large, regenerate it
                            if existing_size > 200000:  # 200KB threshold
                                needs_processing = True
                                self.stdout.write(f"🔄 Large AVIF detected ({existing_size//1024}KB), will regenerate")
                        
                        if not needs_processing:
                            continue
                        
                        if dry_run:
                            self.stdout.write(
                                f"🔍 Would optimize: {filename} "
                                f"({original_size//1024}KB, type: {image_type})"
                            )
                            total_processed += 1
                            continue
                        
                        # Open and process image
                        with Image.open(file_path) as img:
                            # Preserve transparency where present. Do NOT flatten to white.
                            if img.mode == 'P':
                                # Convert palette images to RGBA to keep alpha
                                img = img.convert('RGBA')
                            # If image has alpha (RGBA/LA), keep it; AVIF/WebP support alpha.
                            # Only convert to RGB when there is no alpha channel.
                            if img.mode not in ('RGB', 'RGBA', 'LA'):
                                img = img.convert('RGB')
                            
                            # For very large images, resize first (configurable for backgrounds)
                            if is_background:
                                max_size = int(bg_max_size) if isinstance(bg_max_size, int) else 2400
                            else:
                                max_size = 1200
                            if max_size and max(img.size) > max_size:
                                ratio = max_size / max(img.size)
                                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                                img = img.resize(new_size, Image.Resampling.LANCZOS)
                                self.stdout.write(f"📏 Resized to {new_size}")
                            
                            # Choose quality per type: --bg-quality/--product-quality override, then --quality, else heuristics
                            chosen_quality = None
                            if is_background and isinstance(bg_quality, int):
                                chosen_quality = bg_quality
                            elif (not is_background) and isinstance(product_quality, int):
                                chosen_quality = product_quality
                            elif isinstance(quality, int):
                                chosen_quality = quality

                            # Save optimized AVIF (internal heuristics will adapt if chosen_quality is None)
                            save_avif_optimized(img, avif_path, image_type=image_type, quality=chosen_quality)
                            
                            # Save WebP as fallback
                            # Keep backgrounds crisp enough
                            webp_quality = 82 if is_background else 80
                            save_webp(img, webp_path, quality=webp_quality)
                        
                        # Calculate size after
                        if os.path.exists(avif_path):
                            new_size = os.path.getsize(avif_path)
                            total_size_after += new_size
                            reduction = ((original_size - new_size) / original_size) * 100
                            
                            self.stdout.write(
                                f"✅ {filename}: {original_size//1024}KB → {new_size//1024}KB "
                                f"(-{reduction:.1f}%, type: {image_type})"
                            )
                        else:
                            total_size_after += original_size
                            self.stdout.write(f"⚠️  Failed to create AVIF for {filename}")
                        
                        total_processed += 1
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error processing {file_path}: {e}")
                        )
        
        # Summary
        self.stdout.write(f"\n📊 Summary:")
        if dry_run:
            self.stdout.write(f"   Would process: {total_processed} images")
            self.stdout.write(f"   Total size: {total_size_before//1024//1024}MB")
            self.stdout.write(f"   Run without --dry-run to actually optimize")
        else:
            if total_size_before > 0:
                total_reduction = ((total_size_before - total_size_after) / total_size_before) * 100
                self.stdout.write(f"   Processed: {total_processed} images")
                self.stdout.write(f"   Size before: {total_size_before//1024//1024}MB")
                self.stdout.write(f"   Size after: {total_size_after//1024//1024}MB")
                self.stdout.write(f"   Total reduction: {total_reduction:.1f}%")
                self.stdout.write(f"   Saved: {(total_size_before-total_size_after)//1024//1024}MB")
            else:
                self.stdout.write(f"   No images processed")
        
        self.stdout.write(f"\n💡 Tips:")
        self.stdout.write(f"   • Use --quality 8 for even more aggressive compression")
        self.stdout.write(f"   • Background images use quality={quality} by default")
        self.stdout.write(f"   • Check visual quality after optimization")
