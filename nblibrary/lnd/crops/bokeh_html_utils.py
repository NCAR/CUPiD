"""
Utility functions for creating static HTML viewers with Bokeh controls.

This module provides functions to create interactive HTML pages with dropdown
menus and radio button groups for viewing figures.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from bokeh.layouts import column
from bokeh.layouts import row
from bokeh.models import CustomJS
from bokeh.models import Div
from bokeh.models import RadioButtonGroup
from bokeh.models import Select
from bokeh.plotting import output_file
from bokeh.plotting import save

# pylint: disable=import-error

try:
    from bokeh.io import show, output_notebook

    JUPYTER_AVAILABLE = True
except ImportError:
    JUPYTER_AVAILABLE = False

# Display configuration constants
IMAGE_CONTAINER_WIDTH = 900  # Width of the image container in pixels
IMAGE_CONTAINER_MIN_HEIGHT = 400  # Minimum height of the image container in pixels
IMAGE_MAX_HEIGHT = 800  # Maximum height for displayed images in pixels
RADIO_BUTTON_WIDTH = 200  # Width of radio button groups in pixels


def build_figure_paths(
    output_dir: str,
    controls: list[dict[str, Any]],
    current_combo: list[str] | None = None,
) -> dict[tuple[str, ...], str]:
    """Recursively build all combinations of control options and their file paths.

    This function generates a dictionary mapping all possible combinations of
    control options (from dropdowns and radio buttons) to their corresponding
    figure file paths. It uses recursion to build the Cartesian product of all
    control options.

    Parameters
    ----------
    output_dir : str
        Directory containing the figure files.
    controls : list of dict
        List of control specifications. Each dict should contain:
        - 'type': str, either 'dropdown' or 'radio'
        - 'title': str, the title/label for the control
        - 'options': list of str, the options available
        - 'default': str, the default selected value
    current_combo : list of str, optional
        Current combination being built (used internally for recursion).
        Default is None, which initializes to an empty list.

    Returns
    -------
    dict
        Dictionary mapping tuples of option combinations to file paths.
        Keys are tuples of strings (one element per control, in order).
        Values are strings representing file paths in the format:
        "{output_dir}/{sanitized_option1}_{sanitized_option2}_..._{sanitized_optionN}.png"

    Examples
    --------
    >>> controls = [
    ...     {'type': 'dropdown', 'title': 'Variable', 'options': ['Temp', 'Precip'],
    ...      'default': 'Temp'},
    ...     {'type': 'radio', 'title': 'Season', 'options': ['Summer', 'Winter'],
    ...      'default': 'Summer'}
    ... ]
    >>> paths = build_figure_paths('figures', controls)
    >>> paths[('Temp', 'Summer')]
    'figures/temp_summer.png'
    """
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


def sanitize_filename(name: str) -> str:
    """Convert a figure name to a valid Unix filename prefix.

    Lowercases the name and replaces spaces and illegal characters with underscores.
    Multiple consecutive underscores are collapsed to a single underscore, and
    leading/trailing underscores are removed.

    Parameters
    ----------
    name : str
        The figure name to sanitize.

    Returns
    -------
    str
        The sanitized filename prefix.

    Examples
    --------
    >>> sanitize_filename("Temperature (°C)")
    'temperature_c'
    >>> sanitize_filename("  Multiple   Spaces  ")
    'multiple_spaces'
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


def image_to_data_uri(image_path: str | Path) -> str:
    """Convert an image file to a base64 data URI.

    Reads an image file and converts it to a base64-encoded data URI that can
    be embedded directly in HTML. The MIME type is automatically determined
    from the file extension.

    Parameters
    ----------
    image_path : str or Path
        Path to the image file.

    Returns
    -------
    str
        Base64-encoded data URI for the image in the format:
        "data:{mime_type};base64,{encoded_data}"

    Notes
    -----
    Supported image formats and their MIME types:
    - .png: image/png
    - .jpg, .jpeg: image/jpeg
    - .gif: image/gif
    - .svg: image/svg+xml
    - Other extensions default to image/png
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
    dropdown_specs: list[dict[str, Any]] | None = None,
    radio_specs: list[dict[str, Any]] | None = None,
    output_filename: str = "figure_viewer.html",
    output_dir: str = "matplotlib_figures",
    show_in_notebook: bool = False,
    embed_images: bool | None = None,
    image_max_height: int = IMAGE_MAX_HEIGHT,
) -> None:
    """Create a static HTML file with Bokeh dropdown and radio button controls.

    This function creates an interactive HTML viewer for displaying multiple figures
    with Bokeh controls (dropdown menus and/or radio button groups). The viewer
    allows users to select different combinations of options to display different
    figures. Can be saved as a standalone HTML file or displayed in a Jupyter notebook.

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
        Can be a relative or absolute path.
    show_in_notebook : bool, optional
        If True, display the viewer directly in a Jupyter notebook instead of
        saving to a file. Requires bokeh.io to be available. Default is False.
    embed_images : bool or None, optional
        If True, embed images as base64 data URIs instead of using file paths.
        This makes the HTML self-contained but increases file size. Useful for
        embedding in Jupyter notebooks or sharing single-file HTML documents.
        Default is None, which automatically sets to True if show_in_notebook
        is True, otherwise False.
    image_max_height : int, optional
        Maximum height in pixels for displayed images. Images larger than this
        will be scaled down while maintaining aspect ratio. Default is IMAGE_MAX_HEIGHT (800).

    Raises
    ------
    ValueError
        If both dropdown_specs and radio_specs are None or empty.

    Notes
    -----
    At least one of dropdown_specs or radio_specs must be provided.

    The figure file naming convention is:
    {output_dir}/{sanitized_option1}_{sanitized_option2}_..._{sanitized_optionN}.png
    where options are taken in order from dropdowns first, then radio buttons,
    and each option is sanitized using the sanitize_filename function.

    Examples
    --------
    Create a viewer with one dropdown and one radio button group:

    >>> dropdown_specs = [
    ...     {'title': 'Variable', 'options': ['Temperature', 'Precipitation']}
    ... ]
    >>> radio_specs = [
    ...     {'title': 'Season', 'options': ['Summer', 'Winter'], 'default': 'Summer'}
    ... ]
    >>> create_static_html(
    ...     dropdown_specs=dropdown_specs,
    ...     radio_specs=radio_specs,
    ...     output_filename='my_viewer.html',
    ...     output_dir='my_figures'
    ... )
    """
    if dropdown_specs is None:
        dropdown_specs = []
    if radio_specs is None:
        radio_specs = []
    if embed_images is None:
        embed_images = show_in_notebook

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
        f'style="max-width: 100%; max-height: {image_max_height}px; height: auto; width: auto;">'
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
            sizing_mode="stretch_width",
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

    # Build JavaScript callback
    callback = _build_js(
        radio_specs,
        image_max_height,
        figure_paths,
        image_div,
        dropdowns,
        radio_groups,
    )

    # Attach callback to all controls
    for dropdown in dropdowns:
        dropdown.js_on_change("value", callback)
    for radio_group in radio_groups:
        radio_group.js_on_change("active", callback)

    # Create layout with controls in a row and image below
    all_widgets = dropdowns + radio_groups
    if all_widgets:
        radio_group_row = row(*radio_groups)
        dropdown_row = row(*dropdowns)
        layout = column(radio_group_row, dropdown_row, image_div)
    else:
        layout = column(image_div)

    # Check if in Jupyter notebook
    if JUPYTER_AVAILABLE and show_in_notebook:
        output_notebook(hide_banner=True)
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


def _build_js(
    radio_specs: list[dict[str, Any]],
    image_max_height: int,
    figure_paths: dict[tuple[str, ...], str],
    image_div: Div,
    dropdowns: list[Select],
    radio_groups: list[RadioButtonGroup],
) -> CustomJS:
    """Build JavaScript callback for updating displayed figure based on control selections.

    This internal function generates a Bokeh CustomJS callback that updates the
    displayed image when users interact with dropdown menus or radio button groups.
    The callback constructs a key from the current selections and looks up the
    corresponding image path.

    Parameters
    ----------
    radio_specs : list of dict
        List of radio button group specifications. Each dict should contain:
        - 'options': list of str, the options for the radio button group
    image_max_height : int
        Maximum height in pixels for displayed images.
    figure_paths : dict
        Dictionary mapping tuples of option combinations to image file paths
        or data URIs. Generated by build_figure_paths.
    image_div : bokeh.models.Div
        Bokeh Div widget that displays the image.
    dropdowns : list of bokeh.models.Select
        List of Bokeh Select (dropdown) widgets.
    radio_groups : list of bokeh.models.RadioButtonGroup
        List of Bokeh RadioButtonGroup widgets.

    Returns
    -------
    bokeh.models.CustomJS
        Bokeh CustomJS callback object that updates the image when controls change.

    Notes
    -----
    The JavaScript callback:
    1. Collects current values from all dropdowns (by value)
    2. Collects current values from all radio buttons (by mapping active index to option)
    3. Joins these values with '|||' separator to create a lookup key
    4. Retrieves the corresponding image path from the figure_paths dictionary
    5. Updates the image_div HTML to display the new image

    This is an internal function (indicated by leading underscore) and is not
    intended to be called directly by users.
    """
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
        f"                 'style=\"max-width: 100%; max-height: {image_max_height}px; "
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
    return callback
