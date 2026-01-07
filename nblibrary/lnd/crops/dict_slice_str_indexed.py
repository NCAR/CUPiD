"""
A dict-like mapping from (slice, string) → arbitrary Python object.

With a regular dict, you'll get a warning about slices not being hashable.
"""
from __future__ import annotations


class DictSliceStrIndexed:
    """A dict-like mapping from (slice, string) → arbitrary Python object."""

    def __init__(self):
        self._data = {}

    def _key(self, sl, name):
        if not isinstance(sl, slice):
            raise TypeError("First key must be a slice")
        return (sl.start, sl.stop, sl.step, name)

    def __setitem__(self, key, value):
        sl, name = key
        self._data[self._key(sl, name)] = value

    def __getitem__(self, key):
        sl, name = key
        return self._data.get(self._key(sl, name))

    def __delitem__(self, key):
        sl, name = key
        self._data.pop(self._key(sl, name), None)

    def __contains__(self, key):
        sl, name = key
        return self._key(sl, name) in self._data

    def get(self, sl, name, default=None):
        """Return value corresponding to given (slice, string) key"""
        return self._data.get(self._key(sl, name), default)

    def keys(self):
        """Return iterable of (slice, string) keys."""
        for start, stop, step, name in self._data:
            yield slice(start, stop, step), name

    def items(self):
        """Return iterable of ((slice, string), value) pairs."""
        for (start, stop, step, name), value in self._data.items():
            yield (slice(start, stop, step), name), value

    def values(self):
        """Return iterable of values."""
        return self._data.values()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return self.keys()

    def __repr__(self):
        items = ", ".join(
            f"[{repr(sl)}, {repr(name)}]: {repr(val)}"
            for (sl, name), val in self.items()
        )
        return f"{self.__class__.__name__}({{{items}}})"
