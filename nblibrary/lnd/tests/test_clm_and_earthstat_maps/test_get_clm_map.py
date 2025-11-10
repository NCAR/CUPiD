"""
Unit tests for _get_clm_map() function.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# pylint: disable=wrong-import-position
from clm_and_earthstat_maps import _get_clm_map  # noqa: E402


class TestGetClmMap:
    """Test suite for _get_clm_map() function."""

    @patch("clm_and_earthstat_maps.utils.grid_one_variable")
    @patch("clm_and_earthstat_maps.utils.lon_pm2idl")
    def test_yield_conversion_and_units(
        self,
        mock_lon_pm2idl,
        mock_grid,
        sample_cft_ds,
        sample_gridded_map,
    ):
        """Test that yield is converted correctly with proper units."""
        # Mock returns real DataArray
        mock_grid.return_value = sample_gridded_map.copy()
        mock_lon_pm2idl.return_value = sample_gridded_map.copy()

        result = _get_clm_map(sample_cft_ds, "yield")

        # Verify name and units were set
        assert result.name == "Yield"
        assert result.attrs["units"] == "tons / ha"

        # Verify conversion factor was applied (g/m2 to t/ha)
        expected_factor = 1e-6 * 1e4
        # Original values should be multiplied by conversion factor
        original_max = sample_gridded_map.max().values
        result_max = result.max().values
        assert result_max == pytest.approx(original_max * expected_factor)

    @patch("clm_and_earthstat_maps.utils.grid_one_variable")
    @patch("clm_and_earthstat_maps.utils.lon_pm2idl")
    def test_prod_conversion_and_units(
        self,
        mock_lon_pm2idl,
        mock_grid,
        sample_cft_ds,
        sample_gridded_map,
    ):
        """Test that production is converted correctly with proper units."""
        mock_grid.return_value = sample_gridded_map.copy()
        mock_lon_pm2idl.return_value = sample_gridded_map.copy()

        result = _get_clm_map(sample_cft_ds, "prod")

        # Verify name and units were set
        assert result.name == "Production"
        assert result.attrs["units"] == "Mt"

        # Verify conversion factor was applied (g to Mt)
        expected_factor = 1e-6 * 1e-6
        original_max = sample_gridded_map.max().values
        result_max = result.max().values
        assert result_max == pytest.approx(original_max * expected_factor)

    @patch("clm_and_earthstat_maps.utils.grid_one_variable")
    @patch("clm_and_earthstat_maps.utils.lon_pm2idl")
    def test_area_conversion_and_units(
        self,
        mock_lon_pm2idl,
        mock_grid,
        sample_cft_ds,
        sample_gridded_map,
    ):
        """Test that area is converted correctly with proper units."""
        # Create map with some zeros to test masking
        map_with_zeros = sample_gridded_map.copy()
        map_with_zeros.values[0, 0] = 0
        map_with_zeros.values[1, 1] = -5  # Negative value should be masked

        mock_grid.return_value = map_with_zeros
        mock_lon_pm2idl.return_value = map_with_zeros

        result = _get_clm_map(sample_cft_ds, "area")

        # Verify name and units were set
        assert result.name == "Area"
        assert result.attrs["units"] == "Mha"

        # Verify conversion factor was applied (m2 to Mha)
        expected_factor = 1e-4 * 1e-6

        # Verify masking: values <= 0 should be NaN
        assert np.isnan(result.values[0, 0])
        assert np.isnan(result.values[1, 1])

        # Verify positive values are converted correctly
        positive_mask = map_with_zeros.values > 0
        if np.any(positive_mask):
            original_positive = map_with_zeros.values[positive_mask][0]
            result_positive = result.values[positive_mask][0]
            assert result_positive == pytest.approx(original_positive * expected_factor)

    def test_invalid_stat_input_raises_error(self, sample_cft_ds):
        """Test that invalid stat_input raises NotImplementedError."""
        with pytest.raises(
            NotImplementedError,
            match="_get_clm_map\\(\\) doesn't work for stat_input='invalid'",
        ):
            _get_clm_map(sample_cft_ds, "invalid")

    @patch("clm_and_earthstat_maps.utils.grid_one_variable")
    @patch("clm_and_earthstat_maps.utils.lon_pm2idl")
    def test_grid_one_variable_called_with_result(
        self,
        mock_lon_pm2idl,
        mock_grid,
        sample_cft_ds,
        sample_gridded_map,
    ):
        """Test that grid_one_variable is called with 'result' variable."""
        mock_grid.return_value = sample_gridded_map.copy()
        mock_lon_pm2idl.return_value = sample_gridded_map.copy()

        _get_clm_map(sample_cft_ds, "yield")

        # Verify grid_one_variable was called
        mock_grid.assert_called_once()
        # Second argument should be "result"
        assert mock_grid.call_args[0][1] == "result"

    @patch("clm_and_earthstat_maps.utils.grid_one_variable")
    @patch("clm_and_earthstat_maps.utils.lon_pm2idl")
    def test_lon_pm2idl_is_called(
        self,
        mock_lon_pm2idl,
        mock_grid,
        sample_cft_ds,
        sample_gridded_map,
    ):
        """Test that lon_pm2idl is called to convert longitude format."""
        mock_grid.return_value = sample_gridded_map.copy()
        mock_lon_pm2idl.return_value = sample_gridded_map.copy()

        _get_clm_map(sample_cft_ds, "yield")

        # Verify lon_pm2idl was called
        mock_lon_pm2idl.assert_called_once()

    @patch("clm_and_earthstat_maps.utils.grid_one_variable")
    @patch("clm_and_earthstat_maps.utils.lon_pm2idl")
    def test_all_stat_inputs_produce_valid_output(
        self,
        mock_lon_pm2idl,
        mock_grid,
        sample_cft_ds,
        sample_gridded_map,
    ):
        """Test that all valid stat_inputs produce valid DataArrays."""
        mock_grid.return_value = sample_gridded_map.copy()
        mock_lon_pm2idl.return_value = sample_gridded_map.copy()

        stat_inputs = ["yield", "prod", "area"]
        expected_names = ["Yield", "Production", "Area"]
        expected_units = ["tons / ha", "Mt", "Mha"]

        for stat_input, expected_name, expected_unit in zip(
            stat_inputs,
            expected_names,
            expected_units,
        ):
            result = _get_clm_map(sample_cft_ds, stat_input)

            # Verify it's a DataArray
            assert isinstance(result, xr.DataArray)
            # Verify name and units
            assert result.name == expected_name
            assert result.attrs["units"] == expected_unit
            # Verify it has data
            assert result.size > 0
