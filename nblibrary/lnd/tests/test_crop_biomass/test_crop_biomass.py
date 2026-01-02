"""
Tests for functions in the crop_biomass module.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import xarray as xr

# Add parent directories to path to import plotting_utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# noqa: E402
# pylint: disable=wrong-import-position
from crop_biomass import (  # noqa: E402
    _fill_missing_gc2f_units,
    _get_das_to_combine,
    _get_case_grainc_at_maturity,
    GC2F,
    GC2F_UNITS_SOURCE_VAR,
)


def create_mock_case(name):
    """Helper to create a mock case object."""
    case = Mock()
    case.name = name

    return case


@pytest.fixture(name="mock_case", scope="function")
def fixture_mock_case():
    """Create a mock case object (fresh for each test)."""
    case = create_mock_case("test_case")

    da0 = xr.DataArray(data=np.array([1, 2, 3, 4]), attrs={"units": "kg"})
    da1 = xr.DataArray(data=np.array([5, 6, 7, 8]), attrs={"units": "kg"})
    case.cft_ds = xr.Dataset(
        data_vars={
            "var0": da0,
            "var1": da1,
        },
    )

    return case


def _case_with_gc2f_units_source(mock_case):
    case0 = deepcopy(mock_case)
    case = mock_case
    var_missing_units = GC2F + "_fniaefueirub"
    case.cft_ds = case.cft_ds.rename(
        {
            "var0": GC2F_UNITS_SOURCE_VAR,
            "var1": var_missing_units,
        },
    )
    case.cft_ds = case.cft_ds.merge(case0.cft_ds)
    del case.cft_ds[var_missing_units].attrs["units"]
    return case, var_missing_units


class TestFillMissingGc2fUnits:  # pylint: disable=too-many-public-methods
    """Tests for the _fill_missing_gc2f_units function."""

    def test_basic(self, mock_case):
        """Test basic functionality"""
        case, var_missing_units = _case_with_gc2f_units_source(mock_case)

        var_list = ["var0", "var1", var_missing_units]
        e = AssertionError("Missing units")

        f = io.StringIO()
        with redirect_stdout(f):
            case = _fill_missing_gc2f_units(case, var_list, e)

        units = case.cft_ds[GC2F_UNITS_SOURCE_VAR].attrs["units"]
        stdout = f.getvalue()
        expected_msg = f"{e}; assuming {units} based on {GC2F_UNITS_SOURCE_VAR}"
        assert expected_msg in stdout

        assert "units" in case.cft_ds[var_missing_units].attrs
        assert (
            case.cft_ds[var_missing_units].attrs["units"]
            == case.cft_ds["GRAINC_TO_FOOD_PERHARV"].attrs["units"]
        )
        assert (
            case.cft_ds[var_missing_units].attrs["units_source"]
            == GC2F_UNITS_SOURCE_VAR
        )

    def test_err_source_missing(self, mock_case):
        """Test that error is re-raised if source var missing"""
        case, var_missing_units = _case_with_gc2f_units_source(mock_case)

        # Delete the source var
        case.cft_ds = case.cft_ds.drop_vars(GC2F_UNITS_SOURCE_VAR)

        var_list = ["var0", "var1", var_missing_units]
        msg = "Missing units"
        e = AssertionError(msg)

        with pytest.raises(type(e)) as raised:
            _fill_missing_gc2f_units(case, var_list, e)
        assert msg in str(raised)

    def test_err_source_no_units(self, mock_case):
        """Test that error is re-raised if source var has no units"""
        case, var_missing_units = _case_with_gc2f_units_source(mock_case)

        # Remove units from source var
        del case.cft_ds[GC2F_UNITS_SOURCE_VAR].attrs["units"]

        var_list = ["var0", "var1", var_missing_units]
        msg = "Missing units"
        e = AssertionError(msg)

        with pytest.raises(type(e)) as raised:
            _fill_missing_gc2f_units(case, var_list, e)
        assert msg in str(raised)


class TestGetDasToCombine:  # pylint: disable=too-many-public-methods
    """Tests for the _get_das_to_combine function."""

    def test_basic(self):
        """Test basic functionality"""
        da0 = xr.DataArray(data=np.array([1, 2, 3, 4]), attrs={"units": "kg"})
        da1 = xr.DataArray(data=np.array([5, 6, 7, 8]), attrs={"units": "kg"})
        case = create_mock_case("test_case")
        case.cft_ds = xr.Dataset(
            data_vars={
                "var0": da0,
                "var1": da1,
            },
        )
        var_list = list(case.cft_ds.keys())

        units, result_da = _get_das_to_combine(case, var_list)

        msg = "da0 doesn't match"
        assert np.array_equal(da0, result_da.isel(variable=0).values), msg
        msg = "da1 doesn't match"
        assert np.array_equal(da1, result_da.isel(variable=1).values), msg

        assert "units" in result_da.attrs
        assert result_da.attrs["units"] == units

    def test_err_units_missing(self, mock_case):
        """Test that error is thrown if units not found"""
        case = mock_case
        var_list = list(case.cft_ds.keys())

        # Delete units from one var
        del case.cft_ds["var0"].attrs["units"]

        with pytest.raises(AssertionError):
            _get_das_to_combine(case, var_list)

    def test_err_units_mismatch(self, mock_case):
        """Test that error is thrown if units don't match"""
        case = mock_case
        var_list = list(case.cft_ds.keys())

        # Change units of one var
        new_units = "m"
        # First, make sure it will be a new unit
        for var in case.cft_ds:
            assert case.cft_ds[var].attrs["units"] != new_units
        # Now make the change
        case.cft_ds["var0"].attrs["units"] = new_units

        with pytest.raises(AssertionError):
            _get_das_to_combine(case, var_list)

    def test_gc2f_units_missing_ok(self, mock_case):
        """Test kludge: fill GRAINC_TO_FOOD units with those from GRAINC_TO_FOOD_PERHARV"""
        case, var_missing_units = _case_with_gc2f_units_source(mock_case)

        var_list = ["var0", "var1", var_missing_units]

        # Shouldn't error
        units, result_da = _get_das_to_combine(case, var_list)
        assert "units" in result_da.attrs
        assert result_da.attrs["units"] == units

    def test_masking(self):
        """Test masking of negative values"""
        da0 = xr.DataArray(data=np.array([-1, 0, 3, 4]), attrs={"units": "kg"})
        da1 = xr.DataArray(data=np.array([5, 6, -7, 8]), attrs={"units": "kg"})
        case = create_mock_case("test_case")
        case.cft_ds = xr.Dataset(
            data_vars={
                "var0": da0,
                "var1": da1,
            },
        )
        var_list = list(case.cft_ds.keys())

        case, result_da = _get_das_to_combine(case, var_list)

        result = result_da.isel(variable=0).isnull()
        expected = da0 < 0
        msg = f"Unexpected nulls: Got {result.values}, expected {expected.values}"
        assert np.array_equal(result, expected), msg

        result = result_da.isel(variable=1).isnull()
        expected = da1 < 0
        msg = f"Unexpected nulls: Got {result.values}, expected {expected.values}"
        assert np.array_equal(result, expected), msg


@pytest.fixture(name="mock_case_grainc", scope="function")
def fixture_mock_case_grainc():
    """Create a mock case object with grain C vars (fresh for each test)."""
    case = create_mock_case("test_case")

    # 1d vars that don't contribute to grainC sums
    dims = ["pft"]
    da_excl_0 = xr.DataArray(data=np.array([1, 2, 3, 4]), dims=dims)
    da_excl_1 = da_excl_0 + 4

    # Multi-dimensioned vars that do contribute to sums
    dims = ["mxharvests", "pft"]
    # mxmat mean: 2, 5, 8, 11
    da_incl_0 = xr.DataArray(data=np.array([[1, 4, 7, 10], [3, 6, 9, 12]]), dims=dims)
    da_incl_1 = da_incl_0 * 10

    maturity_level = "USABLE"
    case.cft_ds = xr.Dataset(
        data_vars={
            "var0": da_excl_0,
            "var1": da_excl_1,
            f"GRAINC_TO_SEED_{maturity_level}_PERHARV": da_incl_0,
            f"GRAINC_TO_FOOD_{maturity_level}_PERHARV": da_incl_1,
        },
    )
    attrs = {"units": "kg"}
    for var in case.cft_ds:
        case.cft_ds[var].attrs = attrs
    case.cft_ds[f"{maturity_level}_HARVEST"] = xr.full_like(
        case.cft_ds[f"GRAINC_TO_FOOD_{maturity_level}_PERHARV"],
        fill_value=1,
    )

    return case


class TestGetGrainCAtMaturity:  # pylint: disable=too-many-public-methods
    """Tests for the _get_case_grainc_at_maturity function."""

    def test_basic(self, mock_case_grainc):
        """Test basic functionality"""
        case = mock_case_grainc

        case, var = _get_case_grainc_at_maturity(case)

        result = case.cft_ds[var].values
        expected = np.array([22, 55, 88, 121])
        assert np.array_equal(result, expected)
        assert "units" in case.cft_ds[var].attrs

    def test_ok_missing_seed(self, mock_case_grainc):
        """If one product is missing (here, SEED), calculate with what we do have"""
        case = mock_case_grainc
        case.cft_ds = case.cft_ds.drop_vars("GRAINC_TO_SEED_USABLE_PERHARV")

        f = io.StringIO()
        with redirect_stdout(f):
            case, var = _get_case_grainc_at_maturity(case)

        result = case.cft_ds[var].values
        expected = np.array([20, 50, 80, 110])
        assert np.array_equal(result, expected)

        expected_msg = (
            "test_case: Missing grain C outputs for ['SEED']; including only ['FOOD']"
        )
        assert expected_msg in f.getvalue()

    def test_ok_missing_food(self, mock_case_grainc):
        """If one product is missing (here, FOOD), calculate with what we do have"""
        case = mock_case_grainc
        case.cft_ds = case.cft_ds.drop_vars("GRAINC_TO_FOOD_USABLE_PERHARV")

        f = io.StringIO()
        with redirect_stdout(f):
            case, var = _get_case_grainc_at_maturity(case)

        result = case.cft_ds[var].values
        expected = np.array([2, 5, 8, 11])
        assert np.array_equal(result, expected)

        expected_msg = (
            "test_case: Missing grain C outputs for ['FOOD']; including only ['SEED']"
        )
        assert expected_msg in f.getvalue()

    def test_skip_missing_both(self, mock_case_grainc):
        """If both products are missing, do not calculate"""
        case = mock_case_grainc
        case.cft_ds = case.cft_ds.drop_vars("GRAINC_TO_FOOD_USABLE_PERHARV")
        case.cft_ds = case.cft_ds.drop_vars("GRAINC_TO_SEED_USABLE_PERHARV")

        f = io.StringIO()
        with redirect_stdout(f):
            case, var = _get_case_grainc_at_maturity(case)

        assert var not in case.cft_ds

        expected_msg = (
            "test_case: All grain C product variables missing:"
            + " ['GRAINC_TO_FOOD_USABLE_PERHARV', 'GRAINC_TO_SEED_USABLE_PERHARV']"
        )
        assert expected_msg in f.getvalue()

    def test_masking(self, mock_case_grainc):
        """Test masking functionality with all results expecting at least one contributor"""
        case = mock_case_grainc
        case.cft_ds["GRAINC_TO_SEED_USABLE_PERHARV"].values[0, 0] = -1

        case, var = _get_case_grainc_at_maturity(case)

        result = case.cft_ds[var].values
        expected = np.array([23, 55, 88, 121])
        assert np.array_equal(result, expected)

    def test_masking_all(self, mock_case_grainc):
        """Test masking functionality with one result expecting no contributors"""
        case = mock_case_grainc
        case.cft_ds["GRAINC_TO_SEED_USABLE_PERHARV"].values[0, 0] = -1
        case.cft_ds["GRAINC_TO_SEED_USABLE_PERHARV"].values[1, 0] = -1
        case.cft_ds["GRAINC_TO_FOOD_USABLE_PERHARV"].values[0, 0] = -1
        case.cft_ds["GRAINC_TO_FOOD_USABLE_PERHARV"].values[1, 0] = -1

        case, var = _get_case_grainc_at_maturity(case)

        result = case.cft_ds[var].values
        # If everything is masked, it's taking xarray mean of NaNs, which should give 0
        expected = np.array([0, 55, 88, 121])
        assert np.array_equal(result, expected)
