"""
Unit tests for ResultsMaps._check_vrange_ok_for_key_plot() method.
"""

from __future__ import annotations

import numpy as np
import pytest

from ....crops.results_maps import _check_vrange_ok_for_key_plot, DEFAULT_NO_VRANGE


ERR_REGEX = r"unless vmin \(first value in vrange tuple\) is 0"


class TestCheckVrangeOkForKeyPlot:
    """Test suite for ResultsMaps._check_vrange_ok_for_key_plot() method.

    This method orchestrates colorbar range handling by choosing between:
    1. plot_vranges (per-plot custom ranges)
    2. one_colorbar with shared range
    3. key_plot with shared range (skipping key)
    4. No special handling (individual colorbars already set)
    """

    # pylint: disable=protected-access

    def test_check_vrange_ok_for_key_plot_ok(self):
        """Test _check_vrange_ok_for_key_plot doesn't error if everything's good"""
        _check_vrange_ok_for_key_plot((0, 1987))

    def test_check_vrange_ok_for_key_plot_ok_default(self):
        """Test _check_vrange_ok_for_key_plot doesn't error with default vrange"""
        _check_vrange_ok_for_key_plot(DEFAULT_NO_VRANGE)

    @pytest.mark.parametrize(
        "vrange",
        [
            (1, 1987),
            (-1, 1987),
            (np.inf, 1987),
            (None, 1987),
        ],
    )
    def test_check_vrange_ok_for_key_plot_err_vmin_not0(self, vrange):
        """Test _check_vrange_ok_for_key_plot errors with bad vmin"""
        with pytest.raises(
            NotImplementedError,
            match=ERR_REGEX,
        ):
            _check_vrange_ok_for_key_plot(vrange)

    def test_check_vrange_ok_for_key_plot_err_vmax_none(self):
        """Test _check_vrange_ok_for_key_plot errors with bad vmax"""
        with pytest.raises(
            NotImplementedError,
            match=ERR_REGEX,
        ):
            _check_vrange_ok_for_key_plot((0, None))
