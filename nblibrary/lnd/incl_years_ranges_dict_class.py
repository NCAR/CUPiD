from __future__ import annotations


class InclYrsRangesDict(dict):
    """
    Derived type of dict for storing years included in a plot
    """

    def __init__(self, start_year, end_year):
        super().__init__()
        self._all_years = [start_year, end_year]

    def plot_items(self):
        for k, v in super().items():
            yr_range_str = self.get_yr_range_str(k)
            first_time_slice = f"{v[0]}-01-01"
            last_time_slice = f"{v[1]}-12-31"
            time_slice = slice(first_time_slice, last_time_slice)

            yield (v, yr_range_str, time_slice)

    def add(self, key):
        if key.lower() == "all":
            value = self._all_years
        elif isinstance(key, str):
            value = [int(y) for y in key.split("-")]
        else:
            raise RuntimeError(f"Unrecognized value: {value}")

        # Check
        n = len(value)
        assert n == 2, f"Expected list of length 2, got length {n}"

        # Save
        self[key] = value

    def get_str(self, two_year_list):
        return "-".join(str(y) for y in two_year_list)

    def get_yr_range_str(self, key):
        value = self[key]
        value_str = self.get_str(value)
        if value_str == key:
            return value_str
        return f"{key} ({value_str})"

    def get_yr_range_str_list(self):
        return [self.get_yr_range_str(k) for k in self.keys()]
