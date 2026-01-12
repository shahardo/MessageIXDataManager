#!/usr/bin/env python3
"""
Excel icon generator for MessageIX Data Manager
Creates a simple Excel-style icon for XLSX files
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_excel_icon(size=32):
    """Create a simple Excel icon at specified size"""
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Excel green color
    excel_green = '#217346'

    # Draw a simple spreadsheet icon - rectangle with grid lines
    margin = size * 0.1
    rect_width = size - 2 * margin
    rect_height = size - 2 * margin

    # Draw main rectangle
    draw.rectangle([margin, margin, margin + rect_width, margin + rect_height],
                  fill=excel_green, outline='black', width=1)

    # Draw grid lines for spreadsheet look
    grid_spacing = rect_width / 4
    for i in range(1, 4):
        x = margin + i * grid_spacing
        draw.line([x, margin, x, margin + rect_height], fill='white', width=1)

    grid_spacing_y = rect_height / 3
    for i in range(1, 3):
        y = margin + i * grid_spacing_y
        draw.line([margin, y, margin + rect_width, y], fill='white', width=1)

    return img

def create_excel_icons():
    """Create Excel icons in multiple sizes"""
    sizes = [16, 32, 48, 64]

    icons_dir = os.path.dirname(__file__)

    for size in sizes:
        icon = create_excel_icon(size)
        png_path = os.path.join(icons_dir, f'excel_icon_{size}x{size}.png')
        icon.save(png_path, 'PNG')
        print(f"Created Excel icon: {png_path}")

def main():
    """Generate Excel icon files"""
    print("Generating Excel icons...")
    create_excel_icons()
    print("Excel icon generation complete!")

if __name__ == "__main__":
    main()
