"""
Shared fixtures for clm_and_earthstat_maps tests.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture(name="sample_cft_ds", scope="function")
def fixture_sample_cft_ds():
    """Create a realistic CFT dataset for testing."""
    # Create realistic dimensions
    n_time = 10
    n_pft = 5
    n_lat = 20
    n_lon = 30

    # Create coordinates
    time = np.arange(n_time)
    pft = np.arange(n_pft)
    lat = np.linspace(-90, 90, n_lat)
    lon = np.linspace(-180, 180, n_lon)

    # Create realistic crop data
    # Yield: typically 100-500 g/m2
    crop_yield = np.random.uniform(100, 500, (n_time, n_pft))

    # Production: yield * area (will be calculated)
    crop_area = np.random.uniform(1e4, 1e7, (n_time, n_pft))
    crop_prod = crop_yield * crop_area

    # Create dataset with all required variables
    ds = xr.Dataset(
        {
            "crop_yield": xr.DataArray(
                crop_yield,
                coords={"time": time, "pft": pft},
                dims=["time", "pft"],
                attrs={"units": "g/m2"},
            ),
            "crop_prod": xr.DataArray(
                crop_prod,
                coords={"time": time, "pft": pft},
                dims=["time", "pft"],
                attrs={"units": "g"},
            ),
            "crop_area": xr.DataArray(
                crop_area,
                coords={"time": time, "pft": pft},
                dims=["time", "pft"],
                attrs={"units": "m2"},
            ),
            # Add gridded versions for grid_one_variable to work with
            "pfts1d_lat": xr.DataArray(
                np.repeat(lat, n_pft // n_lat + 1)[:n_pft],
                coords={"pft": pft},
                dims=["pft"],
            ),
            "pfts1d_lon": xr.DataArray(
                np.tile(lon[:n_pft], 1)[:n_pft],
                coords={"pft": pft},
                dims=["pft"],
            ),
        },
        attrs={"resolution": "f09"},
    )

    return ds


@pytest.fixture(name="sample_gridded_map", scope="function")
def fixture_sample_gridded_map():
    """Create a sample gridded map (DataArray) for testing."""
    n_lat = 20
    n_lon = 30

    lat = np.linspace(-90, 90, n_lat)
    lon = np.linspace(-180, 180, n_lon)

    # Create realistic map data
    data = np.random.uniform(0, 100, (n_lat, n_lon))

    da = xr.DataArray(
        data,
        coords={"lat": lat, "lon": lon},
        dims=["lat", "lon"],
        attrs={"units": "test_units"},
    )
    da.name = "Test Map"

    return da
