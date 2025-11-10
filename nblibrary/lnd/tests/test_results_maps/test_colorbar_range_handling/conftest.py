"""
Shared fixtures for ResultsMaps colorbar range handling tests.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import xarray as xr

# Add parent directories to path to import results_maps
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# pylint: disable=wrong-import-position
from results_maps import ResultsMaps  # noqa: E402


@pytest.fixture(name="basic_results_maps")
def fixture_basic_results_maps():
    """Create a basic ResultsMaps instance with sample data."""
    rm = ResultsMaps()

    # Create sample DataArrays with different value ranges
    lat = np.linspace(-90, 90, 10)
    lon = np.linspace(-180, 180, 20)

    # Case 1: values from 0 to 10
    data1 = np.random.uniform(0, 10, (10, 20))
    rm["case1"] = xr.DataArray(
        data1,
        coords={"lat": lat, "lon": lon},
        dims=["lat", "lon"],
        attrs={"units": "test_units"},
    )

    # Case 2: values from -5 to 5
    data2 = np.random.uniform(-5, 5, (10, 20))
    rm["case2"] = xr.DataArray(
        data2,
        coords={"lat": lat, "lon": lon},
        dims=["lat", "lon"],
        attrs={"units": "test_units"},
    )

    # Case 3: values from 20 to 30
    data3 = np.random.uniform(20, 30, (10, 20))
    rm["case3"] = xr.DataArray(
        data3,
        coords={"lat": lat, "lon": lon},
        dims=["lat", "lon"],
        attrs={"units": "test_units"},
    )

    return rm


@pytest.fixture(name="mock_images")
def fixture_mock_images():
    """Create mock image objects for testing with colorbars."""
    images = {}
    for case_name in ["case1", "case2", "case3"]:
        mock_im = Mock()
        mock_im.set_clim = Mock()
        # Add a mock colorbar by default
        mock_colorbar = Mock()
        mock_colorbar.update_normal = Mock()
        mock_im.colorbar = mock_colorbar
        images[case_name] = mock_im
    return images
