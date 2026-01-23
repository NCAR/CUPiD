"""
Unit tests for ResultsMaps._set_shared_colorbar_range() method.
"""

from __future__ import annotations

from unittest.mock import Mock

from ....crops.results_maps import ResultsMaps


class TestSetSharedColorbarRange:
    """Test suite for ResultsMaps._set_shared_colorbar_range() method."""

    # pylint: disable=protected-access

    def test_basic_range_application(self, basic_results_maps, mock_images):
        """Test that vrange is applied to all images when no key plot."""
        subplot_list = ["case1", "case2", "case3"]
        vrange = (0.0, 100.0)

        basic_results_maps._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # All three images should have set_clim called with the vrange
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(0.0, 100.0)
            # Colorbar should be updated
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_skip_key_plot(self, basic_results_maps, mock_images):
        """Test that key plot is skipped when applying range."""
        subplot_list = ["case1", "case2", "case3"]
        vrange = (0.0, 100.0)

        basic_results_maps._set_shared_colorbar_range(
            subplot_list,
            key_plot="case2",
            images=mock_images,
            vrange=vrange,
        )

        # case1 and case3 should have set_clim called
        mock_images["case1"].set_clim.assert_called_once_with(-100.0, 100.0)
        mock_images["case3"].set_clim.assert_called_once_with(-100.0, 100.0)
        # Colorbars should be updated
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
        mock_images["case3"].colorbar.update_normal.assert_called_once_with(
            mock_images["case3"],
        )

        # case2 (key plot) should NOT have set_clim called
        mock_images["case2"].set_clim.assert_not_called()
        mock_images["case2"].colorbar.update_normal.assert_not_called()

    def test_symmetric_0_positive_range(self, mock_images):
        """Test symmetric_0 with positive vmax larger than negative vmin."""
        rm = ResultsMaps(symmetric_0=True)
        subplot_list = ["case1", "case2"]
        vrange = (-5.0, 10.0)  # vmax is larger in absolute value

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # Should symmetrize around zero: max(abs(-5), abs(10)) = 10
        # So vmin=-10, vmax=10
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(-10.0, 10.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_symmetric_0_negative_range(self, mock_images):
        """Test symmetric_0 with negative vmin larger in absolute value."""
        rm = ResultsMaps(symmetric_0=True)
        subplot_list = ["case1", "case2"]
        vrange = (-15.0, 8.0)  # vmin is larger in absolute value

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # Should symmetrize around zero: max(abs(-15), abs(8)) = 15
        # So vmin=-15, vmax=15
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(-15.0, 15.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_symmetric_0_equal_magnitude(self, mock_images):
        """Test symmetric_0 when vmin and vmax have equal magnitude."""
        rm = ResultsMaps(symmetric_0=True)
        subplot_list = ["case1", "case2"]
        vrange = (-10.0, 10.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # Should remain symmetric
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(-10.0, 10.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_symmetric_0_all_positive(self, mock_images):
        """Test symmetric_0 with all positive values."""
        rm = ResultsMaps(symmetric_0=True)
        subplot_list = ["case1", "case2"]
        vrange = (5.0, 20.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # Should symmetrize: max(abs(5), abs(20)) = 20
        # So vmin=-20, vmax=20
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(-20.0, 20.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_symmetric_0_all_negative(self, mock_images):
        """Test symmetric_0 with all negative values."""
        rm = ResultsMaps(symmetric_0=True)
        subplot_list = ["case1", "case2"]
        vrange = (-25.0, -3.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # Should symmetrize: max(abs(-25), abs(-3)) = 25
        # So vmin=-25, vmax=25
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(-25.0, 25.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_no_symmetric_0(self, mock_images):
        """Test that range is not modified when symmetric_0=False."""
        rm = ResultsMaps(symmetric_0=False)
        subplot_list = ["case1", "case2"]
        vrange = (-5.0, 20.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # Should use the range as-is without symmetrizing
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(-5.0, 20.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_single_image(self, mock_images):
        """Test with a single image."""
        rm = ResultsMaps()
        subplot_list = ["case1"]
        vrange = (10.0, 50.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        mock_images["case1"].set_clim.assert_called_once_with(10.0, 50.0)
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
        # Other images should not be touched
        mock_images["case2"].set_clim.assert_not_called()
        mock_images["case3"].set_clim.assert_not_called()

    def test_colorbar_update_when_present(self, basic_results_maps):
        """Test that colorbar is updated when it exists on the image."""
        # Create mock image with a colorbar
        mock_im = Mock()
        mock_im.set_clim = Mock()
        mock_colorbar = Mock()
        mock_colorbar.update_normal = Mock()
        mock_im.colorbar = mock_colorbar

        images = {"case1": mock_im}
        subplot_list = ["case1"]
        vrange = (0.0, 100.0)

        basic_results_maps._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=images,
            vrange=vrange,
        )

        # Both set_clim and colorbar.update_normal should be called
        mock_im.set_clim.assert_called_once_with(0.0, 100.0)
        mock_colorbar.update_normal.assert_called_once_with(mock_im)

    def test_no_colorbar_update_when_absent(self, basic_results_maps):
        """Test that no error occurs when image has no colorbar."""
        # Create mock image without a colorbar
        mock_im = Mock()
        mock_im.set_clim = Mock()
        mock_im.colorbar = None

        images = {"case1": mock_im}
        subplot_list = ["case1"]
        vrange = (0.0, 100.0)

        # Should not raise an error
        basic_results_maps._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=images,
            vrange=vrange,
        )

        # set_clim should still be called
        mock_im.set_clim.assert_called_once_with(0.0, 100.0)

    def test_zero_range(self, mock_images):
        """Test with vmin == vmax (zero range)."""
        rm = ResultsMaps()
        subplot_list = ["case1", "case2"]
        vrange = (5.0, 5.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(5.0, 5.0)
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

    def test_symmetric_0_with_zero_range(self, mock_images):
        """Test symmetric_0 with zero range."""
        rm = ResultsMaps(symmetric_0=True)
        subplot_list = ["case1"]
        vrange = (0.0, 0.0)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        # max(abs(0), abs(0)) = 0, so vmin=-0==0, vmax=0
        mock_images["case1"].set_clim.assert_called_once_with(0.0, 0.0)
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )

    def test_key_plot_first_in_list(self, mock_images):
        """Test when key plot is first in the subplot list."""
        rm = ResultsMaps()
        subplot_list = ["key_case", "case2", "case3"]
        vrange = (0.0, 100.0)

        # Add key_case to mock_images
        mock_im = Mock()
        mock_im.set_clim = Mock()
        mock_colorbar = Mock()
        mock_colorbar.update_normal = Mock()
        mock_im.colorbar = mock_colorbar
        mock_images["key_case"] = mock_im

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot="key_case",
            images=mock_images,
            vrange=vrange,
        )

        # key_case should be skipped
        mock_images["key_case"].set_clim.assert_not_called()
        mock_images["key_case"].colorbar.update_normal.assert_not_called()
        # Others should be updated, symmetric around 0
        mock_images["case2"].set_clim.assert_called_once_with(-100.0, 100.0)
        mock_images["case3"].set_clim.assert_called_once_with(-100.0, 100.0)
        mock_images["case2"].colorbar.update_normal.assert_called_once_with(
            mock_images["case2"],
        )
        mock_images["case3"].colorbar.update_normal.assert_called_once_with(
            mock_images["case3"],
        )

    def test_key_plot_last_in_list(self, mock_images):
        """Test when key plot is last in the subplot list."""
        rm = ResultsMaps()
        subplot_list = ["case1", "case2", "key_case"]
        vrange = (0.0, 100.0)

        # Add key_case to mock_images
        mock_im = Mock()
        mock_im.set_clim = Mock()
        mock_colorbar = Mock()
        mock_colorbar.update_normal = Mock()
        mock_im.colorbar = mock_colorbar
        mock_images["key_case"] = mock_im

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot="key_case",
            images=mock_images,
            vrange=vrange,
        )

        # case1 and case2 should be updated, symmetric around 0
        mock_images["case1"].set_clim.assert_called_once_with(-100.0, 100.0)
        mock_images["case2"].set_clim.assert_called_once_with(-100.0, 100.0)
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
        mock_images["case2"].colorbar.update_normal.assert_called_once_with(
            mock_images["case2"],
        )
        # key_case should be skipped
        mock_images["key_case"].set_clim.assert_not_called()
        mock_images["key_case"].colorbar.update_normal.assert_not_called()

    def test_very_small_range(self, mock_images):
        """Test with very small floating point range."""
        rm = ResultsMaps()
        subplot_list = ["case1"]
        vrange = (1e-15, 1e-14)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        mock_images["case1"].set_clim.assert_called_once_with(1e-15, 1e-14)
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )

    def test_very_large_range(self, mock_images):
        """Test with very large floating point range."""
        rm = ResultsMaps()
        subplot_list = ["case1"]
        vrange = (1e15, 1e16)

        rm._set_shared_colorbar_range(
            subplot_list,
            key_plot=None,
            images=mock_images,
            vrange=vrange,
        )

        mock_images["case1"].set_clim.assert_called_once_with(1e15, 1e16)
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
