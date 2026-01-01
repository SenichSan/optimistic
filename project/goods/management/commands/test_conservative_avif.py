import os
import shutil
from django.core.management.base import BaseCommand
from django.conf import settings
from PIL import Image
from common.image_utils import save_avif_optimized, ensure_dir


class Command(BaseCommand):
    help = "Test conservative AVIF compression on a single file to verify quality"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            required=True,
            help='Path to test file (relative to MEDIA_ROOT or absolute)',
        )
        parser.add_argument(
            '--type',
            type=str,
            default='background',
            choices=['background', 'product', 'icon', 'hero'],
            help='Image type for quality settings',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Create backup of original before testing',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        image_type = options['type']
        create_backup = options['backup']
        
        # Resolve file path
        if not os.path.isabs(file_path):
            file_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if not os.path.exists(file_path):
            self.stdout.write(
                self.style.ERROR(f"❌ File not found: {file_path}")
            )
            return
        
        # Get original file info
        original_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        self.stdout.write(f"\n🔍 Testing conservative AVIF compression:")
        self.stdout.write(f"   📁 File: {filename}")
        self.stdout.write(f"   📏 Original size: {original_size//1024}KB")
        self.stdout.write(f"   🎨 Image type: {image_type}")
        
        # Create backup if requested
        if create_backup:
            backup_path = f"{file_path}.backup"
            if not os.path.exists(backup_path):
                shutil.copy2(file_path, backup_path)
                self.stdout.write(f"   💾 Backup created: {backup_path}")
        
        try:
            # Generate test AVIF
            root, ext = os.path.splitext(file_path)
            test_avif_path = f"{root}_test_conservative.avif"
            
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                
                # Save with conservative settings
                save_avif_optimized(img, test_avif_path, image_type=image_type)
            
            if os.path.exists(test_avif_path):
                avif_size = os.path.getsize(test_avif_path)
                reduction = ((original_size - avif_size) / original_size) * 100
                
                self.stdout.write(f"\n✅ Test AVIF generated successfully:")
                self.stdout.write(f"   📁 Test file: {os.path.basename(test_avif_path)}")
                self.stdout.write(f"   📏 AVIF size: {avif_size//1024}KB")
                self.stdout.write(f"   📉 Reduction: {reduction:.1f}%")
                
                # Quality assessment
                if image_type == 'background':
                    if avif_size < original_size * 0.6:  # Less than 60% of original
                        self.stdout.write(f"   🎯 Quality: GOOD - Conservative compression achieved")
                    else:
                        self.stdout.write(f"   ⚠️  Quality: MINIMAL compression - Consider lower quality if needed")
                
                self.stdout.write(f"\n💡 Next steps:")
                self.stdout.write(f"   1. Check visual quality of: {test_avif_path}")
                self.stdout.write(f"   2. If quality is good, run full regeneration")
                self.stdout.write(f"   3. If quality is poor, increase quality settings")
                
                if create_backup:
                    self.stdout.write(f"   4. Restore from backup if needed: {backup_path}")
                
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to generate test AVIF")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Error processing file: {e}")
            )
        
        # Show quality settings being used
        quality_map = {
            "background": 32,
            "product": 25,
            "icon": 28,
            "hero": 28,
        }
        
        self.stdout.write(f"\n📊 Current conservative quality settings:")
        for img_type, quality in quality_map.items():
            marker = "👈" if img_type == image_type else "  "
            self.stdout.write(f"   {marker} {img_type}: quality={quality}")
