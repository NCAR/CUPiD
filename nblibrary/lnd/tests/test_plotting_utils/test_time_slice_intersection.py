"""
Tests for time slice intersection in the plotting_utils module.
"""

from __future__ import annotations

from unittest.mock import Mock

import cftime
import pytest
import xarray as xr

from ...crops.plotting_utils import (
    _get_range_overlap,
    _get_intsxn_time_slice_of_cases,
    get_instxn_time_slice_of_ds,
    NO_INTSXN_TIME_SLICE,
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


def _create_dataset_w_time(start_year, end_year):
    """Helper to create a dataset with time dimension."""
    if start_year is not None and end_year is not None:
        # Create cftime.DatetimeNoLeap objects for each year
        times = [
            cftime.DatetimeNoLeap(year, 1, 1)
            for year in range(start_year, end_year + 1)
        ]
        ds = xr.Dataset(coords={"time": times})
    else:
        # Empty dataset with no time
        ds = xr.Dataset(coords={"time": []})
    return ds


class TestGetIntsxnTimeSliceIfNeeded:
    """Tests for the _get_intsxn_time_slice_of_cases function."""

    def _create_mock_case(self, name, start_year, end_year):
        """Helper to create a mock case object with time dimension."""
        case = Mock()
        case.name = name

        # Create time coordinate
        case.cft_ds = _create_dataset_w_time(start_year, end_year)

        return case

    def test_no_diff_returns_input_slice(self):
        """Test that when calc_diff_from_key_case is False, input slice is returned."""
        case = self._create_mock_case("case1", 2000, 2010)
        key_case = self._create_mock_case("key_case", 2000, 2010)
        time_slice_in = slice("2005-01-01", "2008-12-31")

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return fallback slice when no overlap
        assert result == NO_INTSXN_TIME_SLICE

    def test_case_subset_of_key_case(self):
        """Test when case range is completely within key_case range."""
        case = self._create_mock_case("case1", 2005, 2010)
        key_case = self._create_mock_case("key_case", 2000, 2015)
        time_slice_in = slice("2000-01-01", "2015-12-31")

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return key_case range (the intersection)
        assert result == slice("2005-01-01", "2010-12-31")

    def test_partial_overlap_at_start(self):
        """Test partial overlap at the start of ranges."""
        case = self._create_mock_case("case1", 1995, 2005)
        key_case = self._create_mock_case("key_case", 2000, 2010)
        time_slice_in = slice("1995-01-01", "2010-12-31")

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
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

        result = _get_intsxn_time_slice_of_cases(
            case,
            key_case,
            time_slice_in,
            calc_diff_from_key_case=True,
        )

        # Should return fallback slice when no overlap
        assert result == NO_INTSXN_TIME_SLICE


class TestGetInstxnTimeSliceOfDs:
    """Tests for the get_instxn_time_slice_of_ds function."""

    def test_single_dataset_returns_its_range(self):
        """Test with a single dataset returns its time range."""
        ds = _create_dataset_w_time(2000, 2010)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds)

        assert result == slice("2000-01-01", "2010-12-31")

    def test_two_datasets_with_overlap(self):
        """Test with two datasets that have overlapping time ranges."""
        ds1 = _create_dataset_w_time(2000, 2015)
        ds2 = _create_dataset_w_time(2005, 2020)
        time_slice_in = slice("2000-01-01", "2020-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return the intersection: 2005-2015
        assert result == slice("2005-01-01", "2015-12-31")

    def test_two_datasets_identical_ranges(self):
        """Test with two datasets that have identical time ranges."""
        ds1 = _create_dataset_w_time(2000, 2010)
        ds2 = _create_dataset_w_time(2000, 2010)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        assert result == slice("2000-01-01", "2010-12-31")

    def test_two_datasets_no_overlap(self):
        """Test with two datasets that have no overlapping time ranges."""
        ds1 = _create_dataset_w_time(2000, 2005)
        ds2 = _create_dataset_w_time(2010, 2015)
        time_slice_in = slice("2000-01-01", "2015-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return NO_INTSXN_TIME_SLICE when no overlap
        assert result == NO_INTSXN_TIME_SLICE

    def test_three_datasets_with_overlap(self):
        """Test with three datasets that all overlap."""
        ds1 = _create_dataset_w_time(2000, 2015)
        ds2 = _create_dataset_w_time(2005, 2020)
        ds3 = _create_dataset_w_time(2008, 2012)
        time_slice_in = slice("2000-01-01", "2020-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2, ds3)

        # Should return the intersection: 2008-2012
        assert result == slice("2008-01-01", "2012-12-31")

    def test_three_datasets_no_common_overlap(self):
        """Test with three datasets where not all overlap."""
        ds1 = _create_dataset_w_time(2000, 2010)
        ds2 = _create_dataset_w_time(2005, 2015)
        ds3 = _create_dataset_w_time(2020, 2025)
        time_slice_in = slice("2000-01-01", "2025-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2, ds3)

        # Should return NO_INTSXN_TIME_SLICE when no common overlap
        assert result == NO_INTSXN_TIME_SLICE

    def test_one_dataset_subset_of_another(self):
        """Test when one dataset's range is completely within another."""
        ds1 = _create_dataset_w_time(2000, 2020)
        ds2 = _create_dataset_w_time(2005, 2010)
        time_slice_in = slice("2000-01-01", "2020-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return the smaller range
        assert result == slice("2005-01-01", "2010-12-31")

    def test_single_year_overlap(self):
        """Test when datasets overlap by only one year."""
        ds1 = _create_dataset_w_time(2000, 2005)
        ds2 = _create_dataset_w_time(2005, 2010)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return single year intersection
        assert result == slice("2005-01-01", "2005-12-31")

    def test_time_slice_narrower_than_datasets(self):
        """Test when time_slice_in is narrower than all datasets."""
        ds1 = _create_dataset_w_time(2000, 2020)
        ds2 = _create_dataset_w_time(2001, 2021)
        time_slice_in = slice("2005-01-01", "2010-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return the narrower slice
        assert result == slice("2005-01-01", "2010-12-31")

    def test_time_slice_wider_than_datasets(self):
        """Test when time_slice_in is wider than all datasets."""
        ds1 = _create_dataset_w_time(2006, 2011)
        ds2 = _create_dataset_w_time(2005, 2010)
        time_slice_in = slice("2000-01-01", "2020-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return the datasets' range
        assert result == slice("2006-01-01", "2010-12-31")

    def test_empty_dataset(self):
        """Test with an empty dataset (no time values)."""
        ds1 = _create_dataset_w_time(2000, 2010)
        ds2 = _create_dataset_w_time(None, None)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return NO_INTSXN_TIME_SLICE when one dataset is empty
        assert result == NO_INTSXN_TIME_SLICE

    def test_multiple_datasets_various_overlaps(self):
        """Test with multiple datasets having various overlap patterns."""
        ds1 = _create_dataset_w_time(2000, 2020)
        ds2 = _create_dataset_w_time(2005, 2018)
        ds3 = _create_dataset_w_time(2008, 2015)
        ds4 = _create_dataset_w_time(2010, 2025)
        time_slice_in = slice("2000-01-01", "2025-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2, ds3, ds4)

        # Should return the intersection: 2010-2015
        assert result == slice("2010-01-01", "2015-12-31")

    def test_partial_overlap_at_boundaries(self):
        """Test datasets that partially overlap at their boundaries."""
        ds1 = _create_dataset_w_time(1995, 2005)
        ds2 = _create_dataset_w_time(2000, 2010)
        ds3 = _create_dataset_w_time(2003, 2015)
        time_slice_in = slice("1995-01-01", "2015-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2, ds3)

        # Should return the intersection: 2003-2005
        assert result == slice("2003-01-01", "2005-12-31")

    def test_time_slice_outside_all_datasets(self):
        """Test when time_slice_in is outside all dataset ranges."""
        ds1 = _create_dataset_w_time(2000, 2005)
        ds2 = _create_dataset_w_time(2000, 2005)
        time_slice_in = slice("2010-01-01", "2015-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return NO_INTSXN_TIME_SLICE when slice is outside datasets
        assert result == NO_INTSXN_TIME_SLICE

    def test_adjacent_non_overlapping_datasets(self):
        """Test datasets that are adjacent but don't overlap."""
        ds1 = _create_dataset_w_time(2000, 2005)
        ds2 = _create_dataset_w_time(2006, 2010)
        time_slice_in = slice("2000-01-01", "2010-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, ds1, ds2)

        # Should return NO_INTSXN_TIME_SLICE for adjacent non-overlapping
        assert result == NO_INTSXN_TIME_SLICE

    def test_many_datasets_with_common_overlap(self):
        """Test with many datasets to ensure scalability."""
        datasets = [_create_dataset_w_time(2000 + i, 2020 - i) for i in range(5)]
        time_slice_in = slice("2000-01-01", "2020-12-31")

        result = get_instxn_time_slice_of_ds(time_slice_in, *datasets)

        # Should return the intersection: 2004-2016
        assert result == slice("2004-01-01", "2016-12-31")
