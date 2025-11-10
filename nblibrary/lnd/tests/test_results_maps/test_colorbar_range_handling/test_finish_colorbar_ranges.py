"""
Unit tests for ResultsMaps._finish_colorbar_ranges() method.
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


class TestFinishColorbarRanges:
    """Test suite for ResultsMaps._finish_colorbar_ranges() method.

    This method orchestrates colorbar range handling by choosing between:
    1. plot_vranges (per-plot custom ranges)
    2. one_colorbar with shared range
    3. key_plot with shared range (skipping key)
    4. No special handling (individual colorbars already set)
    """

    # pylint: disable=protected-access

    def test_plot_vranges_path(self, basic_results_maps, mock_images):
        """Test that plot_vranges takes precedence over other options."""
        # Set up plot_vranges
        basic_results_maps.plot_vranges = {
            "case1": (10.0, 20.0),
            "case2": (30.0, 40.0),
        }

        subplot_list = ["case1", "case2", "case3"]

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=False,
            key_plot=None,
            images=mock_images,
        )

        # case1 and case2 should have their custom ranges applied
        mock_images["case1"].set_clim.assert_called_once_with(10.0, 20.0)
        mock_images["case2"].set_clim.assert_called_once_with(30.0, 40.0)
        # Colorbars should be updated
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
        mock_images["case2"].colorbar.update_normal.assert_called_once_with(
            mock_images["case2"],
        )
        # case3 should not be touched (not in plot_vranges)
        mock_images["case3"].set_clim.assert_not_called()
        mock_images["case3"].colorbar.update_normal.assert_not_called()

    def test_one_colorbar_with_auto_range(self, basic_results_maps, mock_images):
        """Test one_colorbar=True with automatic range calculation."""
        subplot_list = ["case1", "case2", "case3"]

        # When one_colorbar=True, individual images don't have colorbars
        for case_name in subplot_list:
            mock_images[case_name].colorbar = None

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=True,
            key_plot=None,
            images=mock_images,
        )

        # All images should have set_clim called with the same computed range
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once()
            # No individual colorbar updates when one_colorbar=True

        # Verify all got the same range
        case1_args = mock_images["case1"].set_clim.call_args[0]
        case2_args = mock_images["case2"].set_clim.call_args[0]
        case3_args = mock_images["case3"].set_clim.call_args[0]
        assert case1_args == case2_args == case3_args

    def test_one_colorbar_with_explicit_vrange(self, basic_results_maps, mock_images):
        """Test one_colorbar=True with explicit vrange applies it to all subplots."""
        # Set explicit vrange
        basic_results_maps.vrange = (5.0, 15.0)

        subplot_list = ["case1", "case2", "case3"]

        # When one_colorbar=True, individual images don't have colorbars
        for case_name in subplot_list:
            mock_images[case_name].colorbar = None

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=True,
            key_plot=None,
            images=mock_images,
        )

        # All subplots should have the explicit vrange applied
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_called_once_with(5.0, 15.0)
            # No individual colorbar updates when one_colorbar=True

    def test_key_plot_path(self, basic_results_maps, mock_images):
        """Test key_plot triggers shared range calculation."""
        subplot_list = ["case1", "case2", "case3"]

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=False,
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

        # case3 (key plot) should be skipped
        mock_images["case3"].set_clim.assert_not_called()
        mock_images["case3"].colorbar.update_normal.assert_not_called()

        # Verify case1 and case2 got the same range
        case1_args = mock_images["case1"].set_clim.call_args[0]
        case2_args = mock_images["case2"].set_clim.call_args[0]
        assert case1_args == case2_args

    def test_no_special_handling(self, basic_results_maps, mock_images):
        """Test that nothing happens when no special options are set."""
        subplot_list = ["case1", "case2", "case3"]

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=False,
            key_plot=None,
            images=mock_images,
        )

        # Nothing should be called - individual colorbars already set
        for case_name in subplot_list:
            mock_images[case_name].set_clim.assert_not_called()

    @pytest.mark.parametrize(
        "vrange",
        [
            (1987),
            (1, 1986, 1987),
            [1, 1987],
            None,
        ],
    )
    def test_bad_vrange_assertionerror(
        self,
        basic_results_maps,
        vrange,
    ):
        """Test that AssertionError is raised if vrange isn't a 2-element tuple"""
        basic_results_maps.vrange = vrange
        dummy_list = []
        dummy_dict = {}
        dummy_bool = False
        with pytest.raises(
            AssertionError,
            match=r"ResultsMaps\.vrange must be a two-element tuple",
        ):
            basic_results_maps._finish_colorbar_ranges(
                subplot_title_list=dummy_list,
                one_colorbar=dummy_bool,
                key_plot="dummy string",
                images=dummy_dict,
            )

    def test_plot_vranges_with_one_colorbar_assertionerror(
        self,
        basic_results_maps,
        mock_images,
    ):
        """Test that plot_vranges with one_colorbar raises AssertionError."""
        basic_results_maps.plot_vranges = {"case1": (100.0, 200.0)}

        subplot_list = ["case1", "case2"]

        # Should raise AssertionError when both plot_vranges and one_colorbar are set
        with pytest.raises(
            AssertionError,
            match="why did you ask for some of them to have special colorbar limits",
        ):
            basic_results_maps._finish_colorbar_ranges(
                subplot_list,
                one_colorbar=True,
                key_plot=None,
                images=mock_images,
            )

    def test_key_plot_and_one_colorbar_assertionerror(
        self,
        basic_results_maps,
    ):
        """Test that AssertionError is raised if user requests key plot and shared colorbar"""
        dummy_list = []
        dummy_dict = {}
        with pytest.raises(
            AssertionError,
            match="key_plot is not falsy.*it's not possible.*all plots share a colorbar",
        ):
            basic_results_maps._finish_colorbar_ranges(
                subplot_title_list=dummy_list,
                one_colorbar=True,
                key_plot="dummy string",
                images=dummy_dict,
            )

    @pytest.mark.parametrize(
        "vrange",
        [
            (1, 1987),
            (-1, 1987),
            (np.inf, 1987),
            (None, 1987),
            (1, None),
        ],
    )
    def test_key_plot_and_vrange_notimplementederror(
        self,
        basic_results_maps,
        vrange,
    ):
        """
        Test that AssertionError is raised if user requests key plot and overall vrange where vmin
        is not zero
        """
        basic_results_maps.vrange = vrange
        dummy_list = []
        dummy_dict = {}
        with pytest.raises(
            NotImplementedError,
            match="key_plot is not falsy.*not possible to also request a default colorbar range",
        ):
            basic_results_maps._finish_colorbar_ranges(
                subplot_title_list=dummy_list,
                one_colorbar=False,
                key_plot="dummy string",
                images=dummy_dict,
            )

    def test_key_plot_and_vrange_okay_if_vmin_0(
        self,
        basic_results_maps,
        mock_images,
    ):
        """
        Test that, if user requests key plot and overall vrange with vmin (first value in vrange
        tuple) 0, then vrange is applied to key plot and others get (-vmax, vmax).
        """
        vrange = (0, 20)
        basic_results_maps.vrange = vrange
        case_names = list(mock_images.keys())
        key_plot = case_names[0]
        basic_results_maps._finish_colorbar_ranges(
            subplot_title_list=case_names,
            one_colorbar=False,
            key_plot=key_plot,
            images=mock_images,
        )

        vmin, vmax = vrange
        for case_name, im in mock_images.items():
            if case_name == key_plot:
                im.set_clim.assert_called_once_with(vmin, vmax)
            else:
                im.set_clim.assert_called_once_with(-vmax, vmax)
            im.colorbar.update_normal.assert_called_once_with(im)

    def test_plot_vranges_with_key_plot_notimplementederror(
        self,
        basic_results_maps,
        mock_images,
    ):
        """Test that plot_vranges with key_plot raises NotImplementedError."""
        basic_results_maps.plot_vranges = {"case1": (100.0, 200.0)}

        subplot_list = ["case1", "case2"]

        # Should raise NotImplementedError when both plot_vranges and key_plot are set
        with pytest.raises(
            NotImplementedError,
            match="it is not possible to apply special colorbar limits.*while also providing a key plot",
        ):
            basic_results_maps._finish_colorbar_ranges(
                subplot_list,
                one_colorbar=False,
                key_plot="case2",
                images=mock_images,
            )

    def test_empty_plot_vranges_falls_through(self, basic_results_maps, mock_images):
        """Test that empty plot_vranges dict doesn't block other paths."""
        basic_results_maps.plot_vranges = {}  # Empty dict is falsy

        subplot_list = ["case1", "case2"]

        # When one_colorbar=True, individual images don't have colorbars
        for case_name in subplot_list:
            mock_images[case_name].colorbar = None

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=True,
            key_plot=None,
            images=mock_images,
        )

        # Should fall through to one_colorbar path
        mock_images["case1"].set_clim.assert_called_once()
        mock_images["case2"].set_clim.assert_called_once()
        # No individual colorbar updates when one_colorbar=True

    def test_multiple_plot_vranges(self, basic_results_maps, mock_images):
        """Test applying different ranges to multiple plots."""
        basic_results_maps.plot_vranges = {
            "case1": (0.0, 10.0),
            "case2": (20.0, 30.0),
            "case3": (40.0, 50.0),
        }

        subplot_list = ["case1", "case2", "case3"]

        basic_results_maps._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=False,
            key_plot=None,
            images=mock_images,
        )

        # Each should get its own range
        mock_images["case1"].set_clim.assert_called_once_with(0.0, 10.0)
        mock_images["case2"].set_clim.assert_called_once_with(20.0, 30.0)
        mock_images["case3"].set_clim.assert_called_once_with(40.0, 50.0)
        # Colorbars should be updated
        mock_images["case1"].colorbar.update_normal.assert_called_once_with(
            mock_images["case1"],
        )
        mock_images["case2"].colorbar.update_normal.assert_called_once_with(
            mock_images["case2"],
        )
        mock_images["case3"].colorbar.update_normal.assert_called_once_with(
            mock_images["case3"],
        )

    def test_one_colorbar_with_symmetric_0(self, mock_images):
        """Test one_colorbar with symmetric_0 applies symmetrization."""
        rm = ResultsMaps(symmetric_0=True)

        # Create data with known asymmetric range
        data1 = np.array([[-3.0, -1.0], [2.0, 4.0]])
        data2 = np.array([[-2.0, 0.0], [1.0, 3.0]])

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

        # When one_colorbar=True, individual images don't have colorbars
        for case_name in subplot_list:
            mock_images[case_name].colorbar = None

        rm._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=True,
            key_plot=None,
            images=mock_images,
        )

        # Both should get symmetric range
        for case_name in subplot_list:
            call_args = mock_images[case_name].set_clim.call_args[0]
            vmin, vmax = call_args
            # Should be symmetric around zero
            assert vmin == pytest.approx(-vmax)
            # Range is -3 to 4, so symmetric should be -4 to 4
            assert abs(vmax) == pytest.approx(4.0)
            # No individual colorbar updates when one_colorbar=True

    def test_key_plot_with_symmetric_0(self, mock_images):
        """Test key_plot with symmetric_0 applies symmetrization."""
        rm = ResultsMaps(symmetric_0=True)

        # Create data with known ranges
        data1 = np.array([[-2.0, -1.0], [1.0, 2.0]])
        data2 = np.array([[-1.0, 0.0], [1.0, 5.0]])  # Wider range
        data3 = np.array([[100.0, 200.0], [300.0, 400.0]])  # Key plot

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

        # Add key_case to mock_images
        mock_im = Mock()
        mock_im.set_clim = Mock()
        mock_colorbar = Mock()
        mock_colorbar.update_normal = Mock()
        mock_im.colorbar = mock_colorbar
        mock_images["key_case"] = mock_im

        subplot_list = ["case1", "case2", "key_case"]

        rm._finish_colorbar_ranges(
            subplot_list,
            one_colorbar=False,
            key_plot="key_case",
            images=mock_images,
        )

        # case1 and case2 should get symmetric range (skipping key_case)
        for case_name in ["case1", "case2"]:
            call_args = mock_images[case_name].set_clim.call_args[0]
            vmin, vmax = call_args
            # Should be symmetric around zero
            assert vmin == pytest.approx(-vmax)
            # Range is -2 to 5, so symmetric should be -5 to 5
            assert abs(vmax) == pytest.approx(5.0)
            # Colorbar should be updated
            mock_images[case_name].colorbar.update_normal.assert_called_once_with(
                mock_images[case_name],
            )

        # key_case should not be called
        mock_images["key_case"].set_clim.assert_not_called()
        mock_images["key_case"].colorbar.update_normal.assert_not_called()
