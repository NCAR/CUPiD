# ResultsMaps Test Suite

This directory contains comprehensive tests for the `ResultsMaps` class.

## Structure

```
tests/test_results_maps/
├── __init__.py
├── README.md
└── test_colorbar_range_handling/
    ├── __init__.py
    ├── conftest.py                              # Shared fixtures
    ├── test_get_shared_colorbar_range.py
    ├── test_set_shared_colorbar_range.py
    ├── test_get_and_set_shared_colorbar_range.py
    └── test_finish_colorbar_ranges.py
```

## Test Modules

### `test_colorbar_range_handling/`

Tests for colorbar range calculation and application methods:

- **`test_get_shared_colorbar_range.py`**
  - Tests `_get_shared_colorbar_range()` - calculating min/max values across subplots
  - Coverage: basic functionality, key plot handling, NaN handling, edge cases

- **`test_set_shared_colorbar_range.py`**
  - Tests `_set_shared_colorbar_range()` - applying colorbar ranges to images
  - Coverage: range application, key plot skipping, symmetric_0 behavior, colorbar updates

- **`test_get_and_set_shared_colorbar_range.py`**
  - Integration tests for `_get_and_set_shared_colorbar_range()`
  - Coverage: end-to-end flow, key plot integration, symmetric_0 integration

- **`test_finish_colorbar_ranges.py`**
  - Tests `_finish_colorbar_ranges()` - orchestrator for colorbar handling
  - Coverage: decision logic, precedence rules, error handling

### `conftest.py`

Shared fixtures available to all test modules:

- **`basic_results_maps`**: ResultsMaps instance with 3 cases of sample data
- **`mock_images`**: Dictionary of mock matplotlib image objects

## Running Tests

Run all ResultsMaps tests:
```bash
pytest tests/test_results_maps/ -v
```

Run specific test module:
```bash
pytest tests/test_results_maps/test_colorbar_range_handling/test_get_shared_colorbar_range.py -v
```

Run specific test:
```bash
pytest tests/test_results_maps/test_colorbar_range_handling/test_get_shared_colorbar_range.py::TestGetSharedColorbarRange::test_basic_range_no_key_plot -v
```
