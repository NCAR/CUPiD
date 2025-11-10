"""
Unit tests for _mapfig_finishup() function.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add parent directories to path to import results_maps
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# pylint: disable=wrong-import-position
from results_maps import _mapfig_finishup  # noqa: E402


@pytest.fixture(name="mock_fig", scope="function")
def fixture_mock_fig():
    """Create a mock figure object (fresh for each test)."""
    mock_fig = Mock()
    mock_fig.suptitle = Mock()
    mock_fig.subplots_adjust = Mock()
    mock_fig.add_axes = Mock(return_value=Mock())
    mock_fig.colorbar = Mock()
    return mock_fig


@pytest.fixture(name="mock_im", scope="function")
def fixture_mock_im():
    """Create a mock image object (fresh for each test)."""
    return Mock()


@pytest.fixture(name="mock_da", scope="function")
def fixture_mock_da():
    """Create a mock DataArray with units attribute (fresh for each test)."""
    mock_da = Mock()
    mock_da.attrs = {"units": "test_units"}
    return mock_da


@pytest.fixture(name="basic_layout", scope="function")
def fixture_basic_layout():
    """Create a basic layout dictionary for one_colorbar=True (fresh for each test)."""
    return {
        "subplots_adjust_colorbar_top": 0.95,
        "subplots_adjust_colorbar_bottom": 0.2,
        "cbar_ax_rect": (0.2, 0.15, 0.6, 0.03),
    }


class TestMapfigFinishup:
    """Test suite for _mapfig_finishup() function."""

    def test_suptitle_always_added(self, mock_fig, mock_im, mock_da):
        """Test that suptitle is always added to the figure."""
        suptitle = "Test Super Title"

        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle=suptitle,
            layout={},
            one_colorbar=False,
        )

        # Verify suptitle was called with correct arguments
        mock_fig.suptitle.assert_called_once_with(
            suptitle,
            fontsize="x-large",
            fontweight="bold",
        )

    def test_one_colorbar_false_minimal_adjustment(self, mock_fig, mock_im, mock_da):
        """Test that one_colorbar=False only adjusts top spacing."""
        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Test",
            layout={},
            one_colorbar=False,
        )

        # Should only adjust top
        mock_fig.subplots_adjust.assert_called_once_with(top=0.96)
        # Should not add axes or colorbar
        mock_fig.add_axes.assert_not_called()
        mock_fig.colorbar.assert_not_called()

    def test_one_colorbar_true_adds_shared_colorbar(
        self,
        mock_fig,
        mock_im,
        mock_da,
        basic_layout,
    ):
        """Test that one_colorbar=True adds a shared colorbar."""
        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Test",
            layout=basic_layout,
            one_colorbar=True,
        )

        # Should adjust both top and bottom
        mock_fig.subplots_adjust.assert_called_once_with(
            top=0.95 - 0.04,  # subplots_adjust_colorbar_top - 0.04
            bottom=0.2,
        )

        # Should add axes for colorbar
        mock_fig.add_axes.assert_called_once_with(rect=(0.2, 0.15, 0.6, 0.03))

        # Should add colorbar
        cbar_ax = mock_fig.add_axes.return_value
        mock_fig.colorbar.assert_called_once_with(
            mock_im,
            cax=cbar_ax,
            orientation="horizontal",
            label="test_units",
        )

    def test_one_colorbar_uses_layout_parameters(self, mock_fig, mock_im):
        """Test that one_colorbar=True uses all layout parameters correctly."""
        mock_da = Mock()
        mock_da.attrs = {"units": "W/m²"}

        # Custom layout parameters
        layout = {
            "subplots_adjust_colorbar_top": 0.92,
            "subplots_adjust_colorbar_bottom": 0.15,
            "cbar_ax_rect": (0.1, 0.1, 0.8, 0.05),
        }

        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Custom Layout Test",
            layout=layout,
            one_colorbar=True,
        )

        # Verify custom layout parameters were used
        mock_fig.subplots_adjust.assert_called_once_with(
            top=0.92 - 0.04,
            bottom=0.15,
        )
        mock_fig.add_axes.assert_called_once_with(rect=(0.1, 0.1, 0.8, 0.05))

    def test_colorbar_label_from_dataarray_units(
        self,
        mock_fig,
        mock_im,
        basic_layout,
    ):
        """Test that colorbar label comes from DataArray units attribute."""
        mock_da = Mock()
        mock_da.attrs = {"units": "custom_units_xyz"}

        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Test",
            layout=basic_layout,
            one_colorbar=True,
        )

        # Verify colorbar was called with the correct label
        call_kwargs = mock_fig.colorbar.call_args[1]
        assert call_kwargs["label"] == "custom_units_xyz"

    def test_suptitle_formatting(self, mock_fig, mock_im, mock_da):
        """Test that suptitle uses correct font formatting."""
        suptitle = "My Custom Title with Special Characters: 123 & @#$"

        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle=suptitle,
            layout={},
            one_colorbar=False,
        )

        # Verify exact suptitle and formatting
        mock_fig.suptitle.assert_called_once_with(
            suptitle,
            fontsize="x-large",
            fontweight="bold",
        )

    def test_one_colorbar_colorbar_orientation(
        self,
        mock_fig,
        mock_im,
        mock_da,
        basic_layout,
    ):
        """Test that shared colorbar is horizontal."""
        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Test",
            layout=basic_layout,
            one_colorbar=True,
        )

        # Verify colorbar orientation is horizontal
        call_kwargs = mock_fig.colorbar.call_args[1]
        assert call_kwargs["orientation"] == "horizontal"

    def test_one_colorbar_uses_correct_image(self, mock_fig, basic_layout):
        """Test that the correct image object is used for the colorbar."""
        mock_im = Mock()
        mock_im.special_attribute = "unique_identifier"

        mock_da = Mock()
        mock_da.attrs = {"units": "test"}

        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Test",
            layout=basic_layout,
            one_colorbar=True,
        )

        # Verify the correct image object was passed to colorbar
        call_args = mock_fig.colorbar.call_args[0]
        assert call_args[0] is mock_im
        assert call_args[0].special_attribute == "unique_identifier"

    def test_one_colorbar_uses_cbar_ax(self, mock_fig, mock_im, basic_layout):
        """Test that colorbar is added to the correct axes."""
        mock_cbar_ax = Mock()
        mock_cbar_ax.unique_id = "colorbar_axes_123"
        mock_fig.add_axes = Mock(return_value=mock_cbar_ax)

        mock_da = Mock()
        mock_da.attrs = {"units": "test"}

        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="Test",
            layout=basic_layout,
            one_colorbar=True,
        )

        # Verify colorbar was added to the correct axes
        call_kwargs = mock_fig.colorbar.call_args[1]
        assert call_kwargs["cax"] is mock_cbar_ax
        assert call_kwargs["cax"].unique_id == "colorbar_axes_123"

    def test_empty_suptitle(self, mock_fig, mock_im, mock_da):
        """Test with empty suptitle string."""
        _mapfig_finishup(
            fig=mock_fig,
            im=mock_im,
            da=mock_da,
            suptitle="",
            layout={},
            one_colorbar=False,
        )

        # Should still call suptitle, even with empty string
        mock_fig.suptitle.assert_called_once_with(
            "",
            fontsize="x-large",
            fontweight="bold",
        )

    def test_dataarray_without_units_attribute(self, mock_fig, mock_im, basic_layout):
        """Test behavior when DataArray doesn't have units attribute."""
        mock_da = Mock()
        mock_da.attrs = {}  # No units attribute

        # Should raise KeyError when trying to access units
        with pytest.raises(KeyError):
            _mapfig_finishup(
                fig=mock_fig,
                im=mock_im,
                da=mock_da,
                suptitle="Test",
                layout=basic_layout,
                one_colorbar=True,
            )

    def test_fixture_independence(self, mock_fig):
        """Test that fixtures are independent between tests."""
        # This test verifies that mock_fig is fresh and has no prior call history
        # If fixtures were shared, this would fail because previous tests called methods
        assert mock_fig.suptitle.call_count == 0
        assert mock_fig.subplots_adjust.call_count == 0
        assert mock_fig.add_axes.call_count == 0
        assert mock_fig.colorbar.call_count == 0
