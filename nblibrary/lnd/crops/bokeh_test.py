"""
Test module for different image aspect ratios.

Generates images with various dimensions to test the flexible image display
in the Bokeh HTML viewer.
"""
from __future__ import annotations

import os

import matplotlib.pyplot as plt
import numpy as np
from bokeh_html_utils import create_static_html
from bokeh_html_utils import sanitize_filename

# Output directories
OUTPUT_DIR = "matplotlib_figures"
HTML_DIR = "html"


def generate_aspect_ratio_figures():
    """Generate figures with different aspect ratios for testing."""

    # Define aspect ratios to test
    # Format: (name, width_inches, height_inches, pixel_width, pixel_height)
    aspect_ratios = [
        ("Small Landscape (400x300)", 4, 3, 400, 300),
        ("Large Landscape (1200x900)", 12, 9, 1200, 900),
        ("Portrait (600x1000)", 6, 10, 600, 1000),
        ("Wide Landscape (1600x400)", 16, 4, 1600, 400),
        ("Standard (800x600)", 8, 6, 800, 600),
        ("Square (800x800)", 8, 8, 800, 800),
    ]

    # Ensure directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(HTML_DIR, exist_ok=True)

    x = np.linspace(0, 2 * np.pi, 100)

    for name, width_in, height_in, width_px, height_px in aspect_ratios:
        # Calculate DPI to get exact pixel dimensions
        dpi = width_px / width_in

        # Create figure with specific size
        plt.figure(figsize=(width_in, height_in))

        # Create a simple plot
        plt.plot(x, np.sin(x), "b-", linewidth=2)
        plt.plot(x, np.cos(x), "r--", linewidth=2)

        # Add title with dimension info
        plt.title(
            f"{name}\n{width_px}x{height_px} pixels",
            fontsize=14,
            fontweight="bold",
        )
        plt.xlabel("x")
        plt.ylabel("y")
        plt.legend(["sin(x)", "cos(x)"])
        plt.grid(True, alpha=0.3)

        # Save with exact pixel dimensions
        filename = sanitize_filename(name) + ".png"
        plt.savefig(f"{OUTPUT_DIR}/{filename}", dpi=dpi, bbox_inches="tight")
        plt.close()

        print(f"Generated: {filename} ({width_px}x{height_px})")

    print(f"\nGenerated {len(aspect_ratios)} figures with different aspect ratios")


def create_aspect_ratio_viewer():
    """Create HTML viewer for aspect ratio test."""

    # Define dropdown options (must match generated filenames)
    figure_options = [
        "Small Landscape (400x300)",
        "Large Landscape (1200x900)",
        "Portrait (600x1000)",
        "Wide Landscape (1600x400)",
        "Standard (800x600)",
        "Square (800x800)",
    ]

    dropdown_specs = [{"title": "Select Aspect Ratio:", "options": figure_options}]

    # Create HTML viewer
    output_path = os.path.join(HTML_DIR, "test_aspect_ratios.html")
    create_static_html(
        dropdown_specs=dropdown_specs,
        radio_specs=None,
        output_filename=output_path,
        output_dir=f"..{os.sep}{OUTPUT_DIR}",  # Relative path from html/ to matplotlib_figures/
        show_in_notebook=True,
    )

    print(f"\nHTML viewer created: {output_path}")
    print("Open this file in a browser to test different aspect ratios")
