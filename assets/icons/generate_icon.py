#!/usr/bin/env python3
"""
Icon generator for MessageIX Data Manager
Creates a MessageIX logo-inspired icon with clean typography and professional design
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

def create_icon(size=256):
    """Create the application icon at specified size - puzzle/diamond logo on transparent background"""
    import math
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Colors for the logo (from image reference)
    colors = {
        'blue_dark': '#09346B',
        'blue_light': '#1780C4',
        'teal': '#6ED3D6',
        'white': '#FFFFFF',
    }

    cx, cy = size/2, size/2

    # Draw back diamonds
    diag = size * 0.82
    s2 = math.sqrt(2)
    diamond1 = [
        (cx, cy - diag/2),
        (cx + diag/2, cy),
        (cx, cy + diag/2),
        (cx - diag/2, cy),
    ]
    diamond2 = [
        (cx, cy - diag/2 * 0.85),
        (cx + diag/2 * 0.85, cy),
        (cx, cy + diag/2 * 0.85),
        (cx - diag/2 * 0.85, cy),
    ]

    draw.polygon(diamond1, fill=colors['blue_dark'])
    draw.polygon(diamond2, fill=colors['blue_light'])

    # Central puzzle shape
    R = size * 0.27
    white_width = size * 0.045
    # Central teal circle
    draw.ellipse([cx-R, cy-R, cx+R, cy+R], fill=colors['teal'], outline=colors['white'], width=int(white_width))

    # Overlay white puzzle notches for 4 sides
    # Parameters controlling puzzle bump shape
    bump_r = R * 0.42
    for angle in [0, 90, 180, 270]:
        a_rad = math.radians(angle)
        outer = (
            cx + (R + bump_r/2) * math.cos(a_rad),
            cy + (R + bump_r/2) * math.sin(a_rad)
        )
        # The notch is drawn as a white arc intersecting the teal circle from the outside
        bbox = [
            outer[0] - bump_r, outer[1] - bump_r,
            outer[0] + bump_r, outer[1] + bump_r
        ]
        start_angle = angle+45
        end_angle = angle-45
        # Draw white arc (outward half-circle)
        draw.arc(bbox, start=start_angle, end=end_angle, fill=colors['white'], width=int(white_width*1.5))

    # (Optional) Draw white outline again to make sure the bumps are cut cleanly
    draw.ellipse([cx-R, cy-R, cx+R, cy+R], outline=colors['white'], width=int(white_width * 1.25))

    return img


def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_ico_file():
    """Create ICO file with multiple sizes"""
    sizes = [16, 32, 48, 64, 128, 256]

    # Create icons for each size
    icons = []
    for size in sizes:
        icon = create_icon(size)
        # Convert to RGBA if needed and append
        icons.append(icon)

    # Save as ICO with multiple sizes
    ico_path = os.path.join(os.path.dirname(__file__), 'messageix_data_manager.ico')

    # Create ICO with proper multiple sizes
    # Convert images to have indexed color mode for better ICO compatibility
    ico_images = []
    for icon in icons:
        # Convert to P mode (palette) for ICO compatibility
        ico_img = icon.convert('P', palette=Image.ADAPTIVE)
        ico_images.append(ico_img)

    # Save with all sizes
    ico_images[0].save(ico_path, format='ICO', sizes=[(img.size[0], img.size[1]) for img in ico_images], append_images=ico_images[1:])

    # Also save individual PNG files for reference
    for i, icon in enumerate(icons):
        png_path = os.path.join(os.path.dirname(__file__), f'icon_{sizes[i]}x{sizes[i]}.png')
        icon.save(png_path, 'PNG')

    print(f"Created ICO file: {ico_path}")
    print(f"Created PNG files for sizes: {sizes}")

def main():
    """Generate all icon files"""
    print("Generating MessageIX Data Manager icons...")

    # Create ICO file
    create_ico_file()

    print("Icon generation complete!")

if __name__ == "__main__":
    main()
