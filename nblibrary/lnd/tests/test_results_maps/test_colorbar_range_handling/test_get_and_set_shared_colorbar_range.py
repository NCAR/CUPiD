"""
Unit tests for ResultsMaps._get_and_set_shared_colorbar_range() method.
"""

from __future__ import annotations

from unittest.mock import Mock

import numpy as np
import pytest
import xarray as xr

from ....crops.results_maps import ResultsMaps


class TestGetAndSetSharedColorbarRange:
    """Test suite for ResultsMaps._get_and_set_shared_colorbar_range() method.

    This method coordinates _get_shared_colorbar_range() and _set_shared_colorbar_range(),
    so these are integration tests verifying they work together correctly.
    """

    # pylint: disable=protected-access

    def test_basic_integration(self, basic_results_maps, mock_images):
        """Test that get and set work together for basic case."""
        subplot_list = ["case1", "case2", "case3"]

        basic_results_maps._get_and_set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
        )

        # All images should have set_clim called with the computed range
        # We don't know exact values due to random data, but we can verify they were called
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once()
            # Verify it was called with two numeric arguments
            call_args = mock_images[case_name].set_clim.call_args[0]
            assert len(call_args) == 2
            assert isinstance(call_args[0], (int, float))
            assert isinstance(call_args[1], (int, float))
            # vmin should be less than or equal to vmax
            assert call_args[0] <= call_args[1]
            # Colorbar should be updated
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_integration_with_key_plot(self, basic_results_maps, mock_images):
        """Test that key plot is properly skipped in the integration."""
        subplot_list = ["case1", "case2", "case3"]

        basic_results_maps._get_and_set_shared_colorbar_range(
            subplot_list,
            key_plot="case3",
            images=mock_images,
        )

        # case1 and case2 should have set_clim called
        mock_images["case1"].set_clim.assert_called_once()
        mock_images["case2"].set_clim.assert_called_once()
        # Colorbars should be updated
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
        mock_images["case2"].colorbar.update_normal.assert_called_once_with(
            mock_images["case2"],
        )

        # case3 (key plot) should NOT have set_clim called
        mock_images["case3"].set_clim.assert_not_called()
        mock_images["case3"].colorbar.update_normal.assert_not_called()

        # Verify case1 and case2 got the same range
        case1_args = mock_images["case1"].set_clim.call_args[0]
        case2_args = mock_images["case2"].set_clim.call_args[0]
        assert case1_args == case2_args

    def test_integration_with_symmetric_0(self, mock_images):
        """Test that symmetric_0 is properly applied in the integration."""
        rm = ResultsMaps(symmetric_0=True)

        # Create data with known asymmetric range
        data1 = np.array([[-5.0, -2.0], [1.0, 3.0]])
        data2 = np.array([[-3.0, 0.0], [2.0, 4.0]])

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

        subplot_list = ["case1", "case2"]

        rm._get_and_set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
        )

        # Both should be called with symmetric range
        # Range is -5 to 4, so symmetric should be -5 to 5
        for case_name in subplot_list:
            call_args = mock_images[case_name].set_clim.call_args[0]
            vmin, vmax = call_args
            # Should be symmetric around zero
            assert vmin == pytest.approx(-vmax)
            # Should use the larger absolute value (5)
            assert abs(vmax) == pytest.approx(5.0)
            # Colorbar should be updated
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_integration_preserves_colorbar_updates(self, basic_results_maps):
        """Test that colorbar updates are triggered when present."""
        # Create mock image with a colorbar
        mock_im = Mock()
        mock_im.set_clim = Mock()
        mock_colorbar = Mock()
        mock_colorbar.update_normal = Mock()
        mock_im.colorbar = mock_colorbar

        images = {"case1": mock_im}
        subplot_list = ["case1"]

        basic_results_maps._get_and_set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=images,
        )

        # Both set_clim and colorbar update should be called
        mock_im.set_clim.assert_called_once()
        mock_colorbar.update_normal.assert_called_once_with(mock_im)
