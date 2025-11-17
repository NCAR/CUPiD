"""
Tests for time slice intersection in the plotting_utils module.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import Mock

import cftime
import pytest
import xarray as xr

# Add parent directories to path to import plotting_utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# noqa: E402
# pylint: disable=wrong-import-position
from plotting_utils import (  # noqa: E402
    _get_range_overlap,
    _get_intsxn_time_slice_if_needed,
)


class TestGetRangeOverlap:  # pylint: disable=too-many-public-methods
    """Tests for the _get_range_overlap function."""

    def test_two_ranges_with_overlap(self):
        """Test basic case with two overlapping ranges."""
        result = _get_range_overlap([2000, 2010], [2005, 2015])
        assert result == [2005, 2010]

    def test_two_ranges_no_overlap(self):
        """Test two ranges with no overlap."""
        result = _get_range_overlap([2000, 2005], [2010, 2015])
        assert result is None

    def test_adjacent_ranges_no_overlap(self):
        """Test adjacent ranges (touching but not overlapping)."""
        result = _get_range_overlap([2000, 2005], [2006, 2010])
        assert result is None

    def test_adjacent_ranges_with_overlap(self):
        """Test adjacent ranges that share a boundary year."""
        result = _get_range_overlap([2000, 2005], [2005, 2010])
        assert result == [2005, 2005]

    def test_identical_ranges(self):
        """Test with identical ranges."""
        result = _get_range_overlap([2000, 2010], [2000, 2010])
        assert result == [2000, 2010]

    def test_one_range_subset_of_another(self):
        """Test where one range is completely contained in another."""
        result = _get_range_overlap([2000, 2020], [2005, 2010])
        assert result == [2005, 2010]

    def test_single_year_range(self):
        """Test with ranges that are single years."""
        result = _get_range_overlap([2005, 2005], [2005, 2005])
        assert result == [2005, 2005]

    def test_single_year_in_larger_range(self):
        """Test single year range within a larger range."""
        result = _get_range_overlap([2000, 2010], [2005, 2005])
        assert result == [2005, 2005]

    def test_none_none_range_first(self):
        """Test with [None, None] as first argument."""
        result = _get_range_overlap([None, None], [2000, 2010])
        assert result is None

    def test_tuple_input(self):
        """Test that tuples work as well as lists."""
        result = _get_range_overlap((2000, 2010), (2005, 2015))
        assert result == [2005, 2010]

    def test_large_year_values(self):
        """Test with large year values."""
        result = _get_range_overlap([10000, 20000], [15000, 25000])
        assert result == [15000, 20000]

    def test_valid_range_start_equals_end(self):
        """Test that ranges where start == end are valid (single year)."""
        result = _get_range_overlap([2005, 2005], [2000, 2010])
        assert result == [2005, 2005]

    def test_three_ranges_with_overlap(self):
        """Test with three overlapping ranges."""
        result = _get_range_overlap([2000, 2010], [2005, 2015], [2008, 2012])
        assert result == [2008, 2010]

    def test_no_arguments(self):
        """Test with no arguments."""
        result = _get_range_overlap()
        assert result is None

    def test_three_ranges_no_overlap(self):
        """Test three ranges where not all overlap."""
        result = _get_range_overlap([2000, 2010], [2005, 2015], [2020, 2025])
        assert result is None

    def test_multiple_ranges_with_overlap(self):
        """Test with more than three overlapping ranges."""
        result = _get_range_overlap(
            [2000, 2020],
            [2005, 2018],
            [2008, 2015],
            [2010, 2025],
            [2009, 2014],
        )
        assert result == [2010, 2014]

    def test_single_range(self):
        """Test with a single range (should return the range itself)."""
        result = _get_range_overlap([2000, 2010])
        assert result == [2000, 2010]

    def test_none_none_range_middle(self):
        """Test with [None, None] in the middle of multiple ranges."""
        result = _get_range_overlap([2000, 2010], [None, None], [2005, 2015])
        assert result is None

    def test_mixed_list_and_tuple(self):
        """Test mixing lists and tuples."""
        result = _get_range_overlap([2000, 2010], (2005, 2015), [2008, 2012])
        assert result == [2008, 2010]

    def test_reversed_order_ranges(self):
        """Test that order of ranges doesn't matter."""
        result1 = _get_range_overlap([2000, 2010], [2005, 2015], [2008, 2012])
        result2 = _get_range_overlap([2008, 2012], [2000, 2010], [2005, 2015])
        result3 = _get_range_overlap([2005, 2015], [2008, 2012], [2000, 2010])
        assert result1 == result2 == result3 == [2008, 2010]

    def test_many_ranges(self):
        """Test with many ranges to ensure scalability."""
        ranges = [[2000 + i, 2020 - i] for i in range(10)]
        result = _get_range_overlap(*ranges)
        assert result == [2009, 2011]

    def test_backward_compatibility_two_args(self):
        """
        Test that the function maintains backward compatibility
        with original two-argument usage.
        """
        # This mimics the original function's usage pattern
        list0 = [2000, 2010]
        list1 = [2005, 2015]
        result = _get_range_overlap(list0, list1)
        assert result == [2005, 2010]

        # Test the [None, None] case from original
        list0 = [None, None]
        list1 = [2005, 2015]
        result = _get_range_overlap(list0, list1)
        assert result is None

    def test_invalid_range_too_few_elements(self):
        """Test that ranges with fewer than 2 elements raise ValueError."""
        with pytest.raises(ValueError, match="has 1 elements, expected 2"):
            _get_range_overlap([2000])

    def test_invalid_range_too_many_elements(self):
        """Test that ranges with more than 2 elements raise ValueError."""
        with pytest.raises(ValueError, match="has 3 elements, expected 2"):
            _get_range_overlap([2000, 2010, 2020])

    def test_invalid_range_empty(self):
        """Test that empty ranges raise ValueError."""
        with pytest.raises(ValueError, match="has 0 elements, expected 2"):
            _get_range_overlap([])

    def test_invalid_range_end_before_start(self):
        """Test that ranges where end < start raise ValueError."""
        with pytest.raises(ValueError, match="has end < start"):
            _get_range_overlap([2010, 2000])

    def test_invalid_range_in_multiple_ranges(self):
        """Test that invalid range is caught even when mixed with valid ones."""
        with pytest.raises(ValueError, match="has end < start"):
            _get_range_overlap([2000, 2010], [2015, 2005], [2008, 2012])

    def test_none_none_range_second(self):
        """Test with [None, None] as second argument."""
        result = _get_range_overlap([2000, 2010], [None, None])
        assert result is None

    def test_tuple_none_none(self):
        """Test that (None, None) is handled like [None, None]."""
        result = _get_range_overlap((None, None), [2000, 2010])
        assert result is None

    def test_negative_years(self):
        """Test with negative year values (e.g., BCE dates)."""
        result = _get_range_overlap([-100, 100], [-50, 50])
        assert result == [-50, 50]

    def test_invalid_range_position_reported(self):
        """Test that the position of the invalid range is reported."""
        with pytest.raises(ValueError, match="Range at position 1"):
            _get_range_overlap([2000, 2010], [2015, 2005])


class TestGetIntsxnTimeSliceIfNeeded:
    """Tests for the _get_intsxn_time_slice_if_needed function."""

    def _create_mock_case(self, name, start_year, end_year):
        """Helper to create a mock case object with time dimension."""
        case = Mock()
        case.name = name

        # Create time coordinate
        if start_year is not None and end_year is not None:
            # Create cftime.DatetimeNoLeap objects for each year
            times = [
                cftime.DatetimeNoLeap(year, 1, 1)
                for year in range(start_year, end_year + 1)
            ]
            ds = xr.Dataset(
                coords={"time": times},
            )
        else:
            # Empty dataset with no time
            ds = xr.Dataset(coords={"time": []})

        case.cft_ds = ds
        return case

    def test_none_time_slice_returns_none(self):
        """Test that None time_slice_in returns None."""
        case = self._create_mock_case("case1", 2000, 2010)
        key_case = self._create_mock_case("key_case", 2000, 2010)

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            None,
            calc_diff_from_key_case=True,
        )

        assert result is None

    def test_no_diff_returns_input_slice(self):
        """Test that when calc_diff_from_key_case is False, input slice is returned."""
        case = self._create_mock_case("case1", 2000, 2010)
        key_case = self._create_mock_case("key_case", 2000, 2010)
        time_slice_in = slice("2005-01-01", "2008-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=False,
        )

        assert result == time_slice_in

    def test_overlapping_ranges(self):
        """Test with overlapping year ranges between case and key_case."""
        case = self._create_mock_case("case1", 2000, 2015)
        key_case = self._create_mock_case("key_case", 2005, 2020)
        time_slice_in = slice("2000-01-01", "2020-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return the intersection: 2005-2015
        assert result == slice("2005-01-01", "2015-12-31")

    def test_identical_ranges(self):
        """Test with identical year ranges."""
        case = self._create_mock_case("case1", 2000, 2010)
        key_case = self._create_mock_case("key_case", 2000, 2010)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        assert result == slice("2000-01-01", "2010-12-31")

    def test_no_overlap_uses_key_case_range(self):
        """Test that when ranges don't overlap, key_case range is used."""
        case = self._create_mock_case("case1", 2000, 2005)
        key_case = self._create_mock_case("key_case", 2010, 2015)
        time_slice_in = slice("2000-01-01", "2015-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return key_case range when no overlap
        assert result == slice("2010-01-01", "2015-12-31")

    def test_case_subset_of_key_case(self):
        """Test when case range is completely within key_case range."""
        case = self._create_mock_case("case1", 2005, 2010)
        key_case = self._create_mock_case("key_case", 2000, 2015)
        time_slice_in = slice("2000-01-01", "2015-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return case range (the intersection)
        assert result == slice("2005-01-01", "2010-12-31")

    def test_key_case_subset_of_case(self):
        """Test when key_case range is completely within case range."""
        case = self._create_mock_case("case1", 2000, 2015)
        key_case = self._create_mock_case("key_case", 2005, 2010)
        time_slice_in = slice("2000-01-01", "2015-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return key_case range (the intersection)
        assert result == slice("2005-01-01", "2010-12-31")

    def test_key_case_empty_raises_error(self):
        """Test that empty key_case raises NotImplementedError."""
        case = self._create_mock_case("case1", 2000, 2010)
        key_case = self._create_mock_case("key_case", None, None)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        with pytest.raises(
            NotImplementedError,
            match="key case 'key_case' has no years in",
        ):
            _get_intsxn_time_slice_if_needed(
                case,
                key_case,
                time_slice_in,
                calc_diff_from_key_case=True,
            )

    def test_partial_overlap_at_start(self):
        """Test partial overlap at the start of ranges."""
        case = self._create_mock_case("case1", 1995, 2005)
        key_case = self._create_mock_case("key_case", 2000, 2010)
        time_slice_in = slice("1995-01-01", "2010-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return the intersection: 2000-2005
        assert result == slice("2000-01-01", "2005-12-31")

    def test_partial_overlap_at_end(self):
        """Test partial overlap at the end of ranges."""
        case = self._create_mock_case("case1", 2005, 2015)
        key_case = self._create_mock_case("key_case", 2000, 2010)
        time_slice_in = slice("2000-01-01", "2015-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return the intersection: 2005-2010
        assert result == slice("2005-01-01", "2010-12-31")

    def test_single_year_overlap(self):
        """Test when ranges overlap by only one year."""
        case = self._create_mock_case("case1", 2000, 2005)
        key_case = self._create_mock_case("key_case", 2005, 2010)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return single year intersection
        assert result == slice("2005-01-01", "2005-12-31")

    def test_time_slice_narrower_than_data(self):
        """Test when time_slice_in is narrower than available data."""
        case = self._create_mock_case("case1", 2000, 2020)
        key_case = self._create_mock_case("key_case", 2000, 2020)
        time_slice_in = slice("2005-01-01", "2010-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return the intersection within the slice
        assert result == slice("2005-01-01", "2010-12-31")

    def test_case_empty_within_slice(self):
        """Test when case has no data within the time slice."""
        case = self._create_mock_case("case1", 2000, 2005)
        key_case = self._create_mock_case("key_case", 2010, 2015)
        time_slice_in = slice("2010-01-01", "2015-12-31")

        result = _get_intsxn_time_slice_if_needed(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return key_case range when case has no overlap
        assert result == slice("2010-01-01", "2015-12-31")
