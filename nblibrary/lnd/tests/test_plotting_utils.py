"""
Tests for plotting_utils module.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path to import plotting_utils
sys.path.insert(0, str(Path(__file__).parent.parent))

# noqa: E402
# pylint: disable=wrong-import-position
from plotting_utils import (  # noqa: E402
    _get_range_overlap,
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
