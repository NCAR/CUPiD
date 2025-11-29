"""
Unit tests for ResultsMaps._get_shared_colorbar_range() method.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

# Add parent directories to path to import results_maps
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# pylint: disable=wrong-import-position
from results_maps import ResultsMaps  # noqa: E402


class TestGetSharedColorbarRange:
    """Test suite for ResultsMaps._get_shared_colorbar_range() method."""

    # pylint: disable=protected-access

    def test_basic_range_no_key_plot(self, basic_results_maps):
        """Test that method returns correct min/max across all cases when no key plot."""
        subplot_list = ["case1", "case2", "case3"]
        vmin, vmax = basic_results_maps._get_shared_colorbar_range(
            subplot_list,
            key_plot=None,
        )

        # Should get the overall min and max across all three cases
        all_values = np.concatenate(
            [
                basic_results_maps["case1"].values.flatten(),
                basic_results_maps["case2"].values.flatten(),
                basic_results_maps["case3"].values.flatten(),
            ],
        )
        expected_vmin = np.nanmin(all_values)
        expected_vmax = np.nanmax(all_values)

        assert vmin == pytest.approx(expected_vmin)
        assert vmax == pytest.approx(expected_vmax)

    def test_range_with_key_plot(self, basic_results_maps):
        """Test that method skips key plot when calculating range."""
        subplot_list = ["case1", "case2", "case3"]
        vmin, vmax = basic_results_maps._get_shared_colorbar_range(
            subplot_list,
            key_plot="case3",
        )

        # Should only consider case1 and case2, skipping case3
        all_values = np.concatenate(
            [
                basic_results_maps["case1"].values.flatten(),
                basic_results_maps["case2"].values.flatten(),
            ],
        )
        expected_vmin = np.nanmin(all_values)
        expected_vmax = np.nanmax(all_values)

        assert vmin == pytest.approx(expected_vmin)
        assert vmax == pytest.approx(expected_vmax)

        # Verify that case3's range is NOT included by checking that
        # the max is less than case3's minimum (case3 has values 20-30)
        case3_min = np.nanmin(basic_results_maps["case3"].values)
        assert vmax < case3_min  # vmax should be well below case3's range

    def test_single_case_no_key_plot(self):
        """Test with a single case and no key plot."""
        rm = ResultsMaps()
        data = np.array([[1.0, 2.0], [3.0, 4.0]])
        rm["only_case"] = xr.DataArray(
            data,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["only_case"], key_plot=None)

        assert vmin == 1.0
        assert vmax == 4.0

    def test_with_nan_values(self):
        """Test that NaN values are properly handled."""
        rm = ResultsMaps()

        # Create data with NaN values
        data1 = np.array([[1.0, np.nan], [3.0, 4.0]])
        data2 = np.array([[np.nan, 2.0], [5.0, np.nan]])

        rm["case1"] = xr.DataArray(
            data1,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data2,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["case1", "case2"], key_plot=None)

        # Should ignore NaN values
        assert vmin == 1.0
        assert vmax == 5.0

    def test_all_nan_raises_no_error(self):
        """Test that all NaN values does not raise RuntimeError."""
        rm = ResultsMaps()

        # Create data with only NaN values
        data = np.full((2, 2), np.nan)
        rm["nan_case"] = xr.DataArray(
            data,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["nan_case"], key_plot=None)

        # Should keep the original values
        assert vmin == np.inf
        assert vmax == -np.inf

    def test_negative_values(self):
        """Test with all negative values."""
        rm = ResultsMaps()

        data1 = np.array([[-10.0, -5.0], [-3.0, -1.0]])
        data2 = np.array([[-20.0, -15.0], [-8.0, -2.0]])

        rm["case1"] = xr.DataArray(
            data1,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data2,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["case1", "case2"], key_plot=None)

        assert vmin == -20.0
        assert vmax == -1.0

    def test_zero_values(self):
        """Test with data containing zeros."""
        rm = ResultsMaps()

        data = np.array([[0.0, 0.0], [0.0, 0.0]])
        rm["zero_case"] = xr.DataArray(
            data,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["zero_case"], key_plot=None)

        assert vmin == 0.0
        assert vmax == 0.0

    def test_mixed_positive_negative(self):
        """Test with mixed positive and negative values."""
        rm = ResultsMaps()

        data1 = np.array([[-5.0, -2.0], [1.0, 3.0]])
        data2 = np.array([[-10.0, 0.0], [2.0, 8.0]])

        rm["case1"] = xr.DataArray(
            data1,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data2,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["case1", "case2"], key_plot=None)

        assert vmin == -10.0
        assert vmax == 8.0

    def test_key_plot_not_in_list(self):
        """
        Test behavior when key_plot is specified but not in subplot_title_list.

        TODO: Change behavior to throw an error instead of ignoring.
        """
        rm = ResultsMaps()

        data1 = np.array([[1.0, 2.0], [3.0, 4.0]])
        data2 = np.array([[5.0, 6.0], [7.0, 8.0]])

        rm["case1"] = xr.DataArray(
            data1,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data2,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        # key_plot "case3" doesn't exist in the list, so it won't be skipped
        vmin, vmax = rm._get_shared_colorbar_range(["case1", "case2"], key_plot="case3")

        # Should include both cases since "case3" is not in the list
        assert vmin == 1.0
        assert vmax == 8.0

    def test_very_small_values(self):
        """Test with very small floating point values."""
        rm = ResultsMaps()

        data = np.array([[1e-10, 2e-10], [3e-10, 4e-10]])
        rm["small_case"] = xr.DataArray(
            data,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["small_case"], key_plot=None)

        assert vmin == pytest.approx(1e-10)
        assert vmax == pytest.approx(4e-10)

    def test_very_large_values(self):
        """Test with very large floating point values."""
        rm = ResultsMaps()

        data = np.array([[1e10, 2e10], [3e10, 4e10]])
        rm["large_case"] = xr.DataArray(
            data,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["large_case"], key_plot=None)

        assert vmin == pytest.approx(1e10)
        assert vmax == pytest.approx(4e10)

    def test_multiple_cases_with_key_plot_first(self):
        """Test when key_plot is the first case in the list."""
        rm = ResultsMaps()

        data1 = np.array([[100.0, 200.0], [300.0, 400.0]])
        data2 = np.array([[1.0, 2.0], [3.0, 4.0]])
        data3 = np.array([[5.0, 6.0], [7.0, 8.0]])

        rm["key_case"] = xr.DataArray(
            data1,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data2,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case3"] = xr.DataArray(
            data3,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(
            ["key_case", "case2", "case3"],
            key_plot="key_case",
        )

        # Should skip key_case (100-400) and only use case2 (1-4) and case3 (5-8)
        assert vmin == 1.0
        assert vmax == 8.0

    def test_multiple_cases_with_key_plot_last(self):
        """Test when key_plot is the last case in the list."""
        rm = ResultsMaps()

        data1 = np.array([[1.0, 2.0], [3.0, 4.0]])
        data2 = np.array([[5.0, 6.0], [7.0, 8.0]])
        data3 = np.array([[100.0, 200.0], [300.0, 400.0]])

        rm["case1"] = xr.DataArray(
            data1,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data2,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["key_case"] = xr.DataArray(
            data3,
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(
            ["case1", "case2", "key_case"],
            key_plot="key_case",
        )

        # Should skip key_case (100-400) and only use case1 (1-4) and case2 (5-8)
        assert vmin == 1.0
        assert vmax == 8.0

    def test_identical_values_all_cases(self):
        """Test when all cases have identical values."""
        rm = ResultsMaps()

        data = np.array([[5.0, 5.0], [5.0, 5.0]])

        rm["case1"] = xr.DataArray(
            data.copy(),
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )
        rm["case2"] = xr.DataArray(
            data.copy(),
            coords={"lat": [0, 1], "lon": [0, 1]},
            dims=["lat", "lon"],
        )

        vmin, vmax = rm._get_shared_colorbar_range(["case1", "case2"], key_plot=None)

        assert vmin == 5.0
        assert vmax == 5.0
