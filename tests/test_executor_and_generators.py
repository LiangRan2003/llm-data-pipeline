import json
import random

import pandas as pd
import pytest

from executor import execute_cleaning_script
from generate_data import generate_messy_data, generate_messy_logs


def test_execute_cleaning_script_returns_dataframe_without_mutating_input():
    raw = pd.DataFrame(
        {
            "price_string": ["$19.99", "FREE", "USD 20"],
            "metadata": [
                json.dumps({"category": "electronics", "warranty_years": 2}),
                json.dumps({"category": "accessories", "warranty_years": None}),
                "{invalid_json",
            ],
        }
    )
    code = """
def clean_data(df):
    df["price"] = (
        df["price_string"]
        .str.extract(r"([0-9]+(?:\\.[0-9]+)?)")[0]
        .astype(float)
        .fillna(0.0)
    )
    df["metadata_category"] = df["metadata"].apply(
        lambda value: json.loads(value).get("category") if value.startswith("{\\\"") else None
    )
    return df.drop(columns=["price_string"])
"""

    cleaned = execute_cleaning_script(code, raw)

    assert list(cleaned.columns) == ["metadata", "price", "metadata_category"]
    assert cleaned["price"].tolist() == [19.99, 0.0, 20.0]
    assert "price" not in raw.columns


def test_execute_cleaning_script_rejects_missing_or_wrong_contract():
    with pytest.raises(RuntimeError, match="clean_data"):
        execute_cleaning_script("def not_clean_data(df):\n    return df", pd.DataFrame())

    with pytest.raises(RuntimeError, match="Expected clean_data to return a DataFrame"):
        execute_cleaning_script("def clean_data(df):\n    return []", pd.DataFrame())


def test_execute_cleaning_script_reports_original_exception_details():
    code = "def clean_data(df):\n    raise KeyError('missing customer_id')"

    with pytest.raises(RuntimeError) as exc_info:
        execute_cleaning_script(code, pd.DataFrame())

    message = str(exc_info.value)
    assert "Exception type: KeyError" in message
    assert "missing customer_id" in message
    assert "Traceback:" in message


def test_execute_cleaning_script_exposes_pandas_and_json_namespace():
    code = """
def clean_data(df):
    parsed = df["payload"].apply(json.loads)
    return pd.DataFrame({"value": [item["value"] for item in parsed]})
"""

    result = execute_cleaning_script(
        code, pd.DataFrame({"payload": ['{"value": 3}', '{"value": 8}']})
    )

    assert result["value"].tolist() == [3, 8]


def test_generate_messy_sales_data_writes_expected_schema(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    random.seed(7)

    generate_messy_data(num_rows=8, output_file="sales.csv")
    df = pd.read_csv("sales.csv")

    assert len(df) == 8
    assert set(df.columns) == {
        "transaction_id",
        "date",
        "price_string",
        "user_id",
        "product_name",
        "metadata",
    }
    assert df["transaction_id"].str.startswith("TXN-").all()


def test_generated_valid_metadata_has_expected_contract(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    random.seed(17)
    generate_messy_data(num_rows=50, output_file="sales.csv")

    metadata = pd.read_csv("sales.csv")["metadata"]
    valid = [json.loads(value) for value in metadata if value != "{invalid_json"]

    assert valid
    assert all(set(item) == {"category", "warranty_years"} for item in valid)
    assert all(item["category"] in {"electronics", "accessories", "unknown"} for item in valid)


def test_generate_messy_logs_writes_raw_log_column(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    random.seed(11)

    generate_messy_logs(num_rows=6, output_file="logs.csv")
    df = pd.read_csv("logs.csv")

    assert list(df.columns) == ["raw_log"]
    assert len(df) == 6
    assert df["raw_log"].str.contains("HTTP/1.1|ERROR:", regex=True).all()
