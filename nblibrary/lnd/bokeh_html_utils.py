"""
Utility functions for creating static HTML viewers with Bokeh controls.

This module provides functions to create interactive HTML pages with dropdown
menus and radio button groups for viewing figures.
"""
from __future__ import annotations

import base64
import re
from pathlib import Path

from bokeh.layouts import column
from bokeh.layouts import row
from bokeh.models import CustomJS
from bokeh.models import Div
from bokeh.models import RadioButtonGroup
from bokeh.models import Select
from bokeh.plotting import output_file
from bokeh.plotting import save

try:
    from bokeh.io import show, output_notebook

    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False

# Display configuration constants
IMAGE_CONTAINER_WIDTH = 900  # Width of the image container in pixels
IMAGE_CONTAINER_MIN_HEIGHT = 400  # Minimum height of the image container in pixels
IMAGE_MAX_HEIGHT = 800  # Maximum height for displayed images in pixels
DROPDOWN_WIDTH = 300  # Width of dropdown menus in pixels
RADIO_BUTTON_WIDTH = 200  # Width of radio button groups in pixels


def build_figure_paths(output_dir, controls, current_combo=None):
    """Recursively build all combinations of control options."""
    if current_combo is None:
        current_combo = []

    if len(current_combo) == len(controls):
        # Base case: we have a complete combination
        sanitized_parts = [sanitize_filename(opt) for opt in current_combo]
        filename = "_".join(sanitized_parts) + ".png"
        return {tuple(current_combo): f"{output_dir}/{filename}"}

    # Recursive case: add each option from the next control
    result = {}
    current_idx = len(current_combo)
    for option in controls[current_idx]["options"]:
        result.update(
            build_figure_paths(output_dir, controls, current_combo + [option]),
        )
    return result


def sanitize_filename(name):
    """Convert a figure name to a valid Unix filename prefix.

    Lowercases the name and replaces spaces and illegal characters with underscores.

    Parameters
    ----------
    name : str
        The figure name to sanitize.

    Returns
    -------
    str
        The sanitized filename prefix.
    """
    # Lowercase the name
    name = name.lower()
    # Replace spaces and any characters that aren't alphanumeric, dash, or underscore
    name = re.sub(r"[^a-z0-9\-_]", "_", name)
    # Replace multiple consecutive underscores with a single underscore
    name = re.sub(r"_+", "_", name)
    # Remove leading/trailing underscores
    name = name.strip("_")
    return name


def image_to_data_uri(image_path):
    """Convert an image file to a base64 data URI.

    Parameters
    ----------
    image_path : str or Path
        Path to the image file.

    Returns
    -------
    str
        Base64-encoded data URI for the image.
    """
    path = Path(image_path)
    with open(path, "rb") as f:
        image_data = f.read()
    b64_data = base64.b64encode(image_data).decode("utf-8")
    # Determine MIME type from extension
    ext = path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
    }
    mime_type = mime_types.get(ext, "image/png")
    return f"data:{mime_type};base64,{b64_data}"


def create_static_html(
    dropdown_specs=None,
    radio_specs=None,
    output_filename="figure_viewer.html",
    output_dir="matplotlib_figures",
    show_in_notebook=False,
    embed_images=False,
):
    """Create a static HTML file with Bokeh dropdown and radio button controls.

    Parameters
    ----------
    dropdown_specs : list of dict, optional
        List of dropdown menu specifications. Each dict should contain:
        - 'title': str, the title/label for the dropdown
        - 'options': list of str, the options to display
        - 'default': str, optional, the default selected value (defaults to first option)
        Default is None (no dropdown menus).
    radio_specs : list of dict, optional
        List of radio button group specifications. Each dict should contain:
        - 'title': str, the title/label for the radio buttons
        - 'options': list of str, the options to display
        - 'default': str, optional, the default selected value (defaults to first option)
        Default is None (no radio button groups).
    output_filename : str, optional
        Name of the output HTML file. Default is "figure_viewer.html".
        Ignored if show_in_notebook is True.
    output_dir : str, optional
        Directory containing the figure files. Default is "matplotlib_figures".
    show_in_notebook : bool, optional
        If True, display the viewer directly in a Jupyter notebook instead of
        saving to a file. Requires bokeh.io to be available. Default is False.
    embed_images : bool, optional
        If True, embed images as base64 data URIs instead of using file paths.
        This makes the HTML self-contained but increases file size. Useful for
        embedding in Jupyter notebooks. Default is False.

    Raises
    ------
    ValueError
        If both dropdown_specs and radio_specs are None or empty.
    ImportError
        If show_in_notebook is True but bokeh.io is not available.

    Notes
    -----
    At least one of dropdown_specs or radio_specs must be provided.
    The figure file naming convention is:
    {output_dir}/{sanitized_option1}_{sanitized_option2}_..._{sanitized_optionN}.png
    where options are taken in order from dropdowns first, then radio buttons.
    """
    if dropdown_specs is None:
        dropdown_specs = []
    if radio_specs is None:
        radio_specs = []

    if not dropdown_specs and not radio_specs:
        raise ValueError(
            "At least one dropdown or radio button group must be specified",
        )

    # Combine all control specs for easier processing
    all_controls = []
    for spec in dropdown_specs:
        all_controls.append(
            {
                "type": "dropdown",
                "title": spec["title"],
                "options": spec["options"],
                "default": spec.get("default", spec["options"][0]),
            },
        )
    for spec in radio_specs:
        all_controls.append(
            {
                "type": "radio",
                "title": spec["title"],
                "options": spec["options"],
                "default": spec.get("default", spec["options"][0]),
            },
        )

    # Build dictionary mapping all option combinations to file paths
    figure_paths = build_figure_paths(output_dir, all_controls)

    # If embedding images, convert paths to data URIs
    if embed_images:
        figure_paths = {
            combo: image_to_data_uri(path) for combo, path in figure_paths.items()
        }

    # Get initial combination (all defaults)
    initial_combo = tuple(ctrl["default"] for ctrl in all_controls)
    initial_path = figure_paths[initial_combo]

    # Create Div to display the initial image
    # Use flexible sizing that adapts to any image dimensions
    # The image will maintain its aspect ratio and be centered
    image_div = Div(
        text=f'<div style="display: flex; justify-content: center; align-items: center; '
        f'min-height: {IMAGE_CONTAINER_MIN_HEIGHT}px;">'
        f'<img src="{initial_path}" '
        f'style="max-width: 100%; max-height: {IMAGE_MAX_HEIGHT}px; height: auto; width: auto;">'
        f"</div>",
        width=IMAGE_CONTAINER_WIDTH,
        sizing_mode="stretch_width",
    )

    # Create dropdown menus
    dropdowns = []
    for spec in dropdown_specs:
        dropdown = Select(
            title=spec["title"],
            value=spec.get("default", spec["options"][0]),
            options=spec["options"],
            width=DROPDOWN_WIDTH,
        )
        dropdowns.append(dropdown)

    # Create radio button groups
    radio_groups = []
    for spec in radio_specs:
        default_value = spec.get("default", spec["options"][0])
        default_idx = spec["options"].index(default_value)
        radio_group = RadioButtonGroup(
            labels=spec["options"],
            active=default_idx,
            width=RADIO_BUTTON_WIDTH,
        )
        radio_groups.append(radio_group)

    # Build JavaScript code to create option-to-index mappings for radio buttons
    radio_mappings_js = []
    for spec in radio_specs:
        mapping = (
            "{"
            + ", ".join([f'{j}: "{opt}"' for j, opt in enumerate(spec["options"])])
            + "}"
        )
        radio_mappings_js.append(mapping)

    # Build JavaScript code for the callback
    js_code_parts = []
    js_code_parts.append("const selected_options = [];")

    # Add dropdown selections
    for i in range(len(dropdowns)):
        js_code_parts.append(f"selected_options.push(dropdown_{i}.value);")

    # Add radio button selections
    for i in range(len(radio_groups)):
        js_code_parts.append(f"const radio_{i}_map = {radio_mappings_js[i]};")
        js_code_parts.append(f"selected_options.push(radio_{i}_map[radio_{i}.active]);")

    # Build the path lookup
    js_code_parts.append("const key = selected_options.join('|||');")
    js_code_parts.append("const img_path = image_paths[key];")
    js_code_parts.append(
        "image_div.text = '<div style=\"display: flex; justify-content: center; "
        + f"align-items: center; min-height: {IMAGE_CONTAINER_MIN_HEIGHT}px;\">' +",
    )
    js_code_parts.append("                 '<img src=\"' + img_path + '\" ' +")
    js_code_parts.append(
        f"                 'style=\"max-width: 100%; max-height: {IMAGE_MAX_HEIGHT}px; "
        + "height: auto; width: auto;\">' +",
    )
    js_code_parts.append("                 '</div>';")

    js_code = "\n        ".join(js_code_parts)

    # Convert figure_paths to use string keys for JavaScript
    figure_paths_js = {"|||".join(combo): path for combo, path in figure_paths.items()}

    # Build callback args
    callback_args = {"image_div": image_div, "image_paths": figure_paths_js}
    for i, dropdown in enumerate(dropdowns):
        callback_args[f"dropdown_{i}"] = dropdown
    for i, radio_group in enumerate(radio_groups):
        callback_args[f"radio_{i}"] = radio_group

    # JavaScript callback to update displayed figure
    callback = CustomJS(args=callback_args, code=js_code)

    # Attach callback to all controls
    for dropdown in dropdowns:
        dropdown.js_on_change("value", callback)
    for radio_group in radio_groups:
        radio_group.js_on_change("active", callback)

    # Create layout with controls in a row and image below
    all_widgets = dropdowns + radio_groups
    if all_widgets:
        controls_row = row(*all_widgets)
        layout = column(controls_row, image_div)
    else:
        layout = column(image_div)

    # Check if in Jupyter notebook
    if JUPYTER_AVAILABLE and show_in_notebook:
        output_notebook()
        show(layout)
    else:
        # Set output file and save
        output_file(output_filename, title="Figure Viewer")
        save(layout)

        print(f"\nStatic HTML file created: {output_filename}")
        print("You can open this file directly in any web browser!")
        print(
            f"Note: Keep the {output_dir}/ folder in the same "
            "directory as the HTML file.",
        )
