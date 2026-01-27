"""
Module for handling year ranges in crop plotting.

This module defines the InclYrsRangesDict class for managing and formatting year ranges
used in crop analysis plots.
"""

from __future__ import annotations

from collections.abc import Iterator


class InclYrsRangesDict(dict):
    """
    Derived type of dict for storing years included in a plot.

    This class extends dict to provide specialized methods for managing year ranges,
    including formatting and iteration over plot-ready data.

    Attributes
    ----------
    _all_years : list[int]
        List containing [start_year, end_year] representing the full year range.
    """

    def __init__(self, start_year: int, end_year: int) -> None:
        """
        Initialize InclYrsRangesDict instance.

        Parameters
        ----------
        start_year : int
            Starting year of the full range.
        end_year : int
            Ending year of the full range.
        """
        super().__init__()
        self._all_years: list[int] = [start_year, end_year]

    def plot_items(self) -> Iterator[tuple[list[int], str, slice]]:
        """
        Iterate over items formatted for plotting.

        Yields
        ------
        tuple[list[int], str, slice]
            Tuple containing:
            - v: List of [start_year, end_year]
            - yr_range_str: Formatted year range string
            - time_slice: Slice object for selecting time range
        """
        for k, v in super().items():
            yr_range_str = self.get_yr_range_str(k)
            first_time_slice = None if (y := v[0]) is None else f"{y}-01-01"
            last_time_slice = None if (y := v[1]) is None else f"{y}-12-31"
            time_slice = slice(first_time_slice, last_time_slice)

            yield (v, yr_range_str, time_slice)

    def add(self, key: str) -> None:
        """
        Add a year range to the dictionary.

        Parameters
        ----------
        key : str
            Year range key. Can be 'all' (case-insensitive) to use the full range, or a
            hyphen-separated year range like '2000-2010'.

        Raises
        ------
        RuntimeError
            If key format is not recognized.
        AssertionError
            If parsed value is not a list of length 2.
        """
        if key.lower() == "all":
            value = self._all_years
        elif isinstance(key, str):
            value = [int(y) for y in key.split("-")]
        else:
            raise RuntimeError(f"Unrecognized value: {key}")

        # Check
        n = len(value)
        assert n == 2, f"Expected list of length 2, got length {n}"

        # Save
        self[key] = value

    def get_str(self, two_year_list: list[int]) -> str:
        """
        Convert a two-element year list to a hyphen-separated string.

        Parameters
        ----------
        two_year_list : list[int]
            List containing [start_year, end_year].

        Returns
        -------
        str
            Hyphen-separated year range string (e.g., '2000-2010').
        """
        return "-".join(str(y) for y in two_year_list)

    def get_yr_range_str(self, key: str) -> str:
        """
        Get formatted year range string for a key.

        If the key already matches the year range format, returns just the range.
        Otherwise, returns 'key (range)' format.

        Parameters
        ----------
        key : str
            Dictionary key for the year range.

        Returns
        -------
        str
            Formatted year range string.
        """
        value = self[key]
        value_str = self.get_str(value)
        if value_str == key:
            return value_str
        return f"{key} ({value_str})"

    def get_yr_range_str_list(self) -> list[str]:
        """
        Get list of formatted year range strings for all keys.

        Returns
        -------
        list[str]
            List of formatted year range strings.
        """
        return [self.get_yr_range_str(k) for k in self.keys()]
