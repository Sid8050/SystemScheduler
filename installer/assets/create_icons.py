"""
Icon Generator for Endpoint Security Agent

Generates .ico files for the installer.
Run this on a system with PIL/Pillow installed.

Usage:
    python create_icons.py
"""

from PIL import Image, ImageDraw


def create_shield_icon(size=256, color=(16, 185, 129)):
    """Create a shield icon."""
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Shield shape points
    margin = size // 10
    points = [
        (size // 2, margin),           # Top center
        (size - margin, size // 5),    # Top right
        (size - margin, size // 2),    # Middle right
        (size // 2, size - margin),    # Bottom center
        (margin, size // 2),           # Middle left
        (margin, size // 5),           # Top left
    ]

    draw.polygon(points, fill=color)

    # Draw lock symbol in white
    lock_color = (255, 255, 255)
    center_x = size // 2
    center_y = size // 2
    lock_width = size // 4
    lock_height = size // 3

    # Lock body
    draw.rectangle([
        center_x - lock_width // 2,
        center_y - lock_height // 4,
        center_x + lock_width // 2,
        center_y + lock_height // 2
    ], fill=lock_color)

    # Lock shackle (arc)
    shackle_width = lock_width * 3 // 4
    draw.arc([
        center_x - shackle_width // 2,
        center_y - lock_height // 2,
        center_x + shackle_width // 2,
        center_y
    ], 180, 0, fill=lock_color, width=max(3, size // 50))

    return image


def create_upload_icon(size=256, color=(59, 130, 246)):
    """Create an upload arrow icon."""
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = size // 10
    center_x = size // 2

    # Draw circular background
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)

    # Draw upload arrow in white
    arrow_color = (255, 255, 255)
    arrow_width = size // 3
    arrow_height = size // 2

    # Arrow head (triangle pointing up)
    arrow_top = size // 4
    arrow_points = [
        (center_x, arrow_top),                           # Top
        (center_x - arrow_width // 2, arrow_top + arrow_height // 3),  # Bottom left
        (center_x + arrow_width // 2, arrow_top + arrow_height // 3),  # Bottom right
    ]
    draw.polygon(arrow_points, fill=arrow_color)

    # Arrow stem (rectangle)
    stem_width = arrow_width // 3
    draw.rectangle([
        center_x - stem_width // 2,
        arrow_top + arrow_height // 4,
        center_x + stem_width // 2,
        arrow_top + arrow_height
    ], fill=arrow_color)

    # Base line
    line_y = size * 3 // 4
    line_width = arrow_width
    draw.rectangle([
        center_x - line_width // 2,
        line_y,
        center_x + line_width // 2,
        line_y + size // 20
    ], fill=arrow_color)

    return image


def save_ico(image, filename):
    """Save image as .ico with multiple sizes."""
    # ICO format supports multiple sizes
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = [image.resize(s, Image.Resampling.LANCZOS) for s in sizes]

    images[0].save(
        filename,
        format='ICO',
        sizes=sizes,
        append_images=images[1:]
    )
    print(f"Created: {filename}")


def main():
    # Create shield icon (main app icon)
    shield = create_shield_icon(256, (16, 185, 129))  # Green
    save_ico(shield, 'shield.ico')

    # Create upload icon (request tool)
    upload = create_upload_icon(256, (59, 130, 246))  # Blue
    save_ico(upload, 'upload.ico')

    print("\nIcons created successfully!")
    print("Copy these to the installer/assets/ directory.")


if __name__ == "__main__":
    main()
