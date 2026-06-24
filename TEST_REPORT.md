# Test Report

## Summary

Added a focused offline pytest suite for the LLM-powered data pipeline. The tests validate the parts of the project that can be checked deterministically without calling an external LLM API.

## What Is Covered

- Dynamic cleaning-code execution through `execute_cleaning_script`.
- Contract enforcement for generated LLM code:
  - A `clean_data` function must be defined.
  - The function must return a pandas `DataFrame`.
- Input immutability: generated cleaning code receives a copy of the raw data.
- Synthetic sales-data generation schema and row count.
- Synthetic server-log generation schema and log format.

## Why This Matters

The pipeline depends on LLM-generated Python code. These tests pin down the execution boundary around that generated code, so future changes can catch unsafe return types, missing functions, broken mock data, or accidental mutation of raw inputs before a full LLM run is attempted.

## Verification

Command:

```powershell
python -m pytest -q
```

Result:

```text
4 passed
```

## Files Added

- `tests/test_executor_and_generators.py`
